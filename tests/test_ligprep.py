"""Tests for bind-ligprep module: models, CLI, and runner integration.

Run with: pytest tests/test_ligprep.py -v
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from bind_tools.ligprep.cli import app
from bind_tools.ligprep.models import (
    LigPrepInput,
    LigPrepItemResult,
    LigPrepOptions,
    LigPrepRequest,
    LigPrepResult,
    LigPrepSpec,
    LigPrepSummary,
)
from bind_tools.ligprep.runner import check_rdkit_installed, run_prepare

# ── Skip guards ──────────────────────────────────────────────────────────────

requires_rdkit = pytest.mark.skipif(
    not check_rdkit_installed(), reason="RDKit not installed"
)

runner = CliRunner()

# Path to test data
TEST_DATA = Path(__file__).resolve().parent.parent / "test_data"
ERLOTINIB_SDF = TEST_DATA / "erlotinib.sdf"


# ═══════════════════════════════════════════════════════════════════════════════
# Tier 1: Model Tests (always run, no deps, no network)
# ═══════════════════════════════════════════════════════════════════════════════


class TestLigPrepOptions:
    def test_ligprep_options_defaults(self):
        opts = LigPrepOptions()
        assert opts.ph == 7.4
        assert opts.enumerate_tautomers is False
        assert opts.enumerate_protomers is False
        assert opts.max_variants == 4
        assert opts.num_conformers == 1
        assert opts.charge_model == "gasteiger"
        assert opts.output_formats == ["sdf"]
        assert opts.engine.value == "auto"

    def test_ligprep_options_alias_roundtrip(self):
        opts = LigPrepOptions(
            enumerateTautomers=True,
            numConformers=5,
            chargeModel="mmff94",
            outputFormats=["sdf", "pdbqt"],
        )
        assert opts.enumerate_tautomers is True
        assert opts.num_conformers == 5
        assert opts.charge_model == "mmff94"
        assert opts.output_formats == ["sdf", "pdbqt"]
        dumped = opts.model_dump(by_alias=True)
        assert "enumerateTautomers" in dumped
        assert "numConformers" in dumped
        assert "chargeModel" in dumped
        assert "outputFormats" in dumped
        assert dumped["enumerateTautomers"] is True
        assert dumped["numConformers"] == 5

    def test_ligprep_options_ph_validation(self):
        with pytest.raises(ValidationError):
            LigPrepOptions(ph=-1.0)
        with pytest.raises(ValidationError):
            LigPrepOptions(ph=15.0)


class TestLigPrepInput:
    def test_ligprep_input_from_smiles(self):
        inp = LigPrepInput(smiles="CC(=O)Oc1ccccc1C(=O)O")
        assert inp.smiles == "CC(=O)Oc1ccccc1C(=O)O"
        assert inp.sdf_path is None
        assert inp.mol2_path is None
        assert inp.pubchem_cid is None
        assert inp.name is None

    def test_ligprep_input_from_sdf_path(self):
        inp = LigPrepInput(sdfPath="/tmp/mol.sdf")
        assert inp.sdf_path == "/tmp/mol.sdf"
        assert inp.smiles is None

    def test_ligprep_input_from_pubchem_cid(self):
        inp = LigPrepInput(pubchemCid=2244)
        assert inp.pubchem_cid == 2244

    def test_ligprep_input_alias_roundtrip(self):
        inp = LigPrepInput(sdfPath="/tmp/mol.sdf", pubchemCid=123)
        dumped = inp.model_dump(by_alias=True)
        assert "sdfPath" in dumped
        assert "pubchemCid" in dumped


class TestLigPrepSpec:
    def test_ligprep_spec_construction(self):
        ligands = [
            LigPrepInput(smiles="CCO"),
            LigPrepInput(sdfPath="/tmp/mol.sdf"),
        ]
        spec = LigPrepSpec(ligands=ligands)
        assert len(spec.ligands) == 2
        assert spec.manifest_path is None
        assert spec.options.ph == 7.4

    def test_ligprep_spec_with_manifest(self):
        spec = LigPrepSpec(manifestPath="/tmp/ligands.csv")
        assert spec.manifest_path == "/tmp/ligands.csv"
        assert spec.ligands == []


class TestLigPrepItemResult:
    def test_ligprep_item_result_succeeded(self):
        item = LigPrepItemResult(
            id="lig_0",
            inputQuery="CCO",
            status="succeeded",
            canonicalSmiles="CCO",
            netCharge=0,
            rotatableBonds=0,
            molecularWeight=46.042,
            logp=-0.001,
            sdfPath="/tmp/lig_0/lig_0.sdf",
            numConformers=1,
        )
        assert item.status == "succeeded"
        assert item.canonical_smiles == "CCO"
        assert item.net_charge == 0
        assert item.sdf_path == "/tmp/lig_0/lig_0.sdf"
        assert item.num_conformers == 1

    def test_ligprep_item_result_failed(self):
        item = LigPrepItemResult(
            id="lig_1",
            inputQuery="INVALID",
            status="failed",
            errors=["Invalid SMILES: INVALID"],
        )
        assert item.status == "failed"
        assert len(item.errors) == 1
        assert item.canonical_smiles is None
        assert item.sdf_path is None


class TestLigPrepSummary:
    def test_ligprep_summary_model(self):
        summary = LigPrepSummary(
            total=3,
            succeeded=2,
            failed=1,
            items=[
                LigPrepItemResult(id="a", status="succeeded"),
                LigPrepItemResult(id="b", status="succeeded"),
                LigPrepItemResult(id="c", status="failed", errors=["bad"]),
            ],
            engineUsed="rdkit",
            engineVersion="2024.03.1",
        )
        assert summary.total == 3
        assert summary.succeeded == 2
        assert summary.failed == 1
        assert len(summary.items) == 3
        assert summary.engine_used == "rdkit"

        dumped = summary.model_dump(by_alias=True)
        assert "engineUsed" in dumped
        assert "engineVersion" in dumped
        assert dumped["engineUsed"] == "rdkit"


class TestLigPrepRequest:
    def test_ligprep_request_envelope(self):
        spec = LigPrepSpec(ligands=[LigPrepInput(smiles="CCO")])
        req = LigPrepRequest(spec=spec)
        assert req.kind == "LigPrepRequest"
        assert req.api_version == "binding.dev/v1"
        assert req.metadata is not None
        assert req.metadata.request_id.startswith("req-")


class TestLigPrepResult:
    def test_ligprep_result_construction(self):
        result = LigPrepResult()
        assert result.kind == "LigPrepResult"
        assert result.tool == "ligprep"
        assert result.status == "succeeded"
        assert result.summary == {}

    def test_ligprep_result_to_json(self):
        result = LigPrepResult()
        js = result.to_json()
        parsed = json.loads(js)
        assert parsed["kind"] == "LigPrepResult"
        assert "apiVersion" in parsed
        assert "runtimeSeconds" in parsed


# ═══════════════════════════════════════════════════════════════════════════════
# Tier 2: CLI Tests (always run, typer.testing.CliRunner)
# ═══════════════════════════════════════════════════════════════════════════════


class TestCLI:
    def test_cli_doctor(self):
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "rdkit" in result.output
        assert "obabel" in result.output
        assert "meeko" in result.output

    def test_cli_schema(self):
        result = runner.invoke(app, ["schema"])
        assert result.exit_code == 0
        assert "LigPrepRequest" in result.output
        assert "LigPrepResult" in result.output

    def test_cli_prepare_no_input_exits_2(self):
        result = runner.invoke(app, ["prepare"])
        assert result.exit_code == 2

    def test_cli_prepare_dry_run_smiles(self):
        result = runner.invoke(
            app,
            ["prepare", "--ligand", "CC(=O)Oc1ccccc1C(=O)O", "--dry-run"],
        )
        assert result.exit_code == 0
        assert "Dry run" in result.output
        assert "1 ligand" in result.output

    def test_cli_prepare_dry_run_sdf(self):
        if not ERLOTINIB_SDF.exists():
            pytest.skip("test_data/erlotinib.sdf not found")
        result = runner.invoke(
            app,
            ["prepare", "--ligand", str(ERLOTINIB_SDF), "--dry-run"],
        )
        assert result.exit_code == 0
        assert "Dry run" in result.output

    def test_cli_prepare_dry_run_output_formats(self):
        result = runner.invoke(
            app,
            [
                "prepare",
                "--ligand", "CCO",
                "--output-formats", "sdf,pdbqt",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "sdf" in result.output
        assert "pdbqt" in result.output

    def test_cli_prepare_dry_run_custom_options(self):
        result = runner.invoke(
            app,
            [
                "prepare",
                "--ligand", "CCO",
                "--ph", "6.5",
                "--num-conformers", "3",
                "--charge-model", "mmff94",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "Dry run" in result.output
        assert "6.5" in result.output
        assert "mmff94" in result.output


# ═══════════════════════════════════════════════════════════════════════════════
# Tier 3: Runner Tests (require RDKit)
# ═══════════════════════════════════════════════════════════════════════════════


@requires_rdkit
class TestRunner:
    def test_prepare_single_from_sdf(self, tmp_path):
        if not ERLOTINIB_SDF.exists():
            pytest.skip("test_data/erlotinib.sdf not found")

        spec = LigPrepSpec(
            ligands=[LigPrepInput(sdfPath=str(ERLOTINIB_SDF))],
        )
        summary = run_prepare(spec, tmp_path / "artifacts")
        assert summary["total"] == 1
        assert summary["succeeded"] == 1
        items = summary["items"]
        assert len(items) == 1
        assert items[0]["status"] == "succeeded"
        assert items[0]["sdfPath"] is not None
        assert Path(items[0]["sdfPath"]).exists()

    def test_prepare_single_from_smiles(self, tmp_path):
        # Aspirin SMILES
        spec = LigPrepSpec(
            ligands=[LigPrepInput(smiles="CC(=O)Oc1ccccc1C(=O)O")],
        )
        summary = run_prepare(spec, tmp_path / "artifacts")
        assert summary["total"] == 1
        assert summary["succeeded"] == 1
        items = summary["items"]
        assert items[0]["status"] == "succeeded"
        assert items[0]["sdfPath"] is not None
        assert Path(items[0]["sdfPath"]).exists()

    def test_prepare_pdbqt_output(self, tmp_path):
        from bind_tools.ligprep.runner import check_meeko_installed, check_obabel_installed

        if not check_meeko_installed() and not check_obabel_installed():
            pytest.skip("Neither meeko nor obabel available for PDBQT output")

        spec = LigPrepSpec(
            ligands=[LigPrepInput(smiles="CCO")],
            options=LigPrepOptions(outputFormats=["sdf", "pdbqt"]),
        )
        summary = run_prepare(spec, tmp_path / "artifacts")
        assert summary["succeeded"] == 1
        items = summary["items"]
        assert items[0]["pdbqtPath"] is not None
        assert Path(items[0]["pdbqtPath"]).exists()

    def test_prepare_properties_computed(self, tmp_path):
        spec = LigPrepSpec(
            ligands=[LigPrepInput(smiles="CC(=O)Oc1ccccc1C(=O)O")],
        )
        summary = run_prepare(spec, tmp_path / "artifacts")
        item = summary["items"][0]
        assert item["molecularWeight"] is not None
        assert item["molecularWeight"] > 0
        assert item["logp"] is not None
        assert item["rotatableBonds"] is not None
        assert item["netCharge"] is not None

    def test_prepare_batch_from_manifest(self, tmp_path):
        # Create a temp CSV manifest with 3 SMILES
        manifest_path = tmp_path / "ligands.csv"
        with open(manifest_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "smiles"])
            writer.writerow(["ethanol", "CCO"])
            writer.writerow(["methanol", "CO"])
            writer.writerow(["propanol", "CCCO"])

        spec = LigPrepSpec(manifestPath=str(manifest_path))
        summary = run_prepare(spec, tmp_path / "artifacts")
        assert summary["total"] == 3
        assert summary["succeeded"] == 3
        assert len(summary["items"]) == 3

    def test_prepare_continue_on_error(self, tmp_path):
        spec = LigPrepSpec(
            ligands=[
                LigPrepInput(smiles="CCO", id="good_1"),
                LigPrepInput(smiles="INVALID_NOT_A_SMILES_STRING", id="bad_1"),
                LigPrepInput(smiles="CO", id="good_2"),
            ],
        )
        summary = run_prepare(spec, tmp_path / "artifacts")
        assert summary["total"] == 3
        assert summary["succeeded"] == 2
        assert summary["failed"] == 1

        items_by_id = {it["id"]: it for it in summary["items"]}
        assert items_by_id["good_1"]["status"] == "succeeded"
        assert items_by_id["bad_1"]["status"] == "failed"
        assert len(items_by_id["bad_1"]["errors"]) > 0
        assert items_by_id["good_2"]["status"] == "succeeded"
