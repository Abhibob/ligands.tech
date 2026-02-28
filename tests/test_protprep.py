"""Tests for bind-protprep module: models, CLI, and integration.

Run with: pytest tests/test_protprep.py -v
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from bind_tools.protprep.cli import app
from bind_tools.protprep.models import (
    ProtPrepOptions,
    ProtPrepRequest,
    ProtPrepResult,
    ProtPrepSpec,
    ProtPrepStepResult,
    ProtPrepSteps,
    ProtPrepSummary,
)
from bind_tools.protprep.runner import (
    check_openmm_installed,
    check_pdb2pqr_installed,
    check_pdbfixer_installed,
)

# ── Skip guards ──────────────────────────────────────────────────────────────

requires_pdbfixer = pytest.mark.skipif(
    not check_pdbfixer_installed(), reason="pdbfixer not installed"
)

runner = CliRunner()


# ── Helper ───────────────────────────────────────────────────────────────────


async def _download_1crn(dest_dir: Path) -> str:
    from bind_tools.protein.pdb_data import download_structure

    return await download_structure("1CRN", dest_dir, format="pdb")


# ═══════════════════════════════════════════════════════════════════════════════
# Tier 1: Model Tests (always run, no deps, no network)
# ═══════════════════════════════════════════════════════════════════════════════


class TestProtPrepSteps:
    def test_protprep_steps_defaults(self):
        steps = ProtPrepSteps()
        assert steps.add_hydrogens is True
        assert steps.fill_missing_residues is True
        assert steps.fill_missing_atoms is True
        assert steps.remove_heterogens is True
        assert steps.remove_water is True
        assert steps.replace_nonstandard is True
        assert steps.assign_protonation is True
        assert steps.energy_minimize is True

    def test_protprep_steps_alias_roundtrip(self):
        steps = ProtPrepSteps(addHydrogens=False, energyMinimize=False)
        assert steps.add_hydrogens is False
        assert steps.energy_minimize is False
        dumped = steps.model_dump(by_alias=True)
        assert "addHydrogens" in dumped
        assert "energyMinimize" in dumped
        assert dumped["addHydrogens"] is False
        assert dumped["energyMinimize"] is False


class TestProtPrepOptions:
    def test_protprep_options_defaults(self):
        opts = ProtPrepOptions()
        assert opts.ph == 7.4
        assert opts.chains == []
        assert opts.keep_water_within is None
        assert opts.force_field == "amber14-all.xml"
        assert opts.water_model == "implicit"
        assert opts.max_minimize_iterations == 500
        assert opts.minimize_tolerance_kj == 10.0

    def test_protprep_options_custom(self):
        opts = ProtPrepOptions(
            ph=6.5,
            chains=["A", "B"],
            keepWaterWithin=5.0,
            forceField="charmm36.xml",
            maxMinimizeIterations=1000,
        )
        assert opts.ph == 6.5
        assert opts.chains == ["A", "B"]
        assert opts.keep_water_within == 5.0
        assert opts.force_field == "charmm36.xml"
        assert opts.max_minimize_iterations == 1000
        dumped = opts.model_dump(by_alias=True)
        assert dumped["keepWaterWithin"] == 5.0
        assert dumped["forceField"] == "charmm36.xml"

    def test_protprep_options_ph_validation(self):
        with pytest.raises(ValidationError):
            ProtPrepOptions(ph=-1.0)
        with pytest.raises(ValidationError):
            ProtPrepOptions(ph=15.0)


class TestProtPrepSpec:
    def test_protprep_spec_from_input_path(self):
        spec = ProtPrepSpec(inputPath="/tmp/protein.pdb")
        assert spec.input_path == "/tmp/protein.pdb"
        assert spec.pdb_id is None
        assert spec.output_format == "pdb"

    def test_protprep_spec_from_pdb_id(self):
        spec = ProtPrepSpec(pdbId="1CRN")
        assert spec.pdb_id == "1CRN"
        assert spec.input_path is None

    def test_protprep_spec_deserialization(self):
        raw = {
            "inputPath": "/data/test.pdb",
            "outputFormat": "cif",
            "steps": {"addHydrogens": False, "removeWater": False},
            "options": {"ph": 6.0, "chains": ["A"]},
        }
        spec = ProtPrepSpec.model_validate(raw)
        assert spec.input_path == "/data/test.pdb"
        assert spec.output_format == "cif"
        assert spec.steps.add_hydrogens is False
        assert spec.steps.remove_water is False
        # Non-specified steps keep defaults
        assert spec.steps.fill_missing_residues is True
        assert spec.options.ph == 6.0
        assert spec.options.chains == ["A"]


class TestProtPrepRequest:
    def test_protprep_request_construction(self):
        spec = ProtPrepSpec(pdbId="1CRN")
        req = ProtPrepRequest(spec=spec)
        assert req.kind == "ProtPrepRequest"
        assert req.api_version == "binding.dev/v1"
        assert req.metadata is not None
        assert req.metadata.request_id.startswith("req-")


class TestProtPrepResult:
    def test_protprep_result_construction(self):
        result = ProtPrepResult()
        assert result.kind == "ProtPrepResult"
        assert result.tool == "protprep"
        assert result.status == "succeeded"
        assert result.summary == {}

    def test_protprep_result_to_json(self):
        result = ProtPrepResult()
        js = result.to_json()
        parsed = json.loads(js)
        assert parsed["kind"] == "ProtPrepResult"
        assert "apiVersion" in parsed
        assert "runtimeSeconds" in parsed

    def test_protprep_result_to_dict(self):
        result = ProtPrepResult()
        d = result.to_dict()
        assert d["kind"] == "ProtPrepResult"
        assert "apiVersion" in d
        assert "runtimeSeconds" in d
        assert isinstance(d, dict)


class TestProtPrepStepResult:
    def test_protprep_step_result_model(self):
        # Applied variant
        applied = ProtPrepStepResult(
            step="add_hydrogens", applied=True, details="Added 100 H", count=100
        )
        assert applied.step == "add_hydrogens"
        assert applied.applied is True
        assert applied.skipped_reason is None
        assert applied.count == 100

        # Skipped variant
        skipped = ProtPrepStepResult(
            step="energy_minimize",
            applied=False,
            skippedReason="OpenMM not installed",
        )
        assert skipped.applied is False
        assert skipped.skipped_reason == "OpenMM not installed"


class TestProtPrepSummary:
    def test_protprep_summary_model(self):
        summary = ProtPrepSummary(
            hydrogensAdded=42,
            residuesFilled=2,
            atomsFilled=5,
            outputPath="/tmp/out.pdb",
            chainsSelected=["A"],
            stepResults=[
                ProtPrepStepResult(step="add_hydrogens", applied=True, count=42),
            ],
        )
        assert summary.hydrogens_added == 42
        assert summary.residues_filled == 2
        assert summary.atoms_filled == 5
        assert summary.output_path == "/tmp/out.pdb"
        assert summary.chains_selected == ["A"]
        assert len(summary.step_results) == 1

        dumped = summary.model_dump(by_alias=True)
        assert "hydrogensAdded" in dumped
        assert "residuesFilled" in dumped
        assert "outputPath" in dumped
        assert "stepResults" in dumped


# ═══════════════════════════════════════════════════════════════════════════════
# Tier 2: CLI Tests (always run, typer.testing.CliRunner)
# ═══════════════════════════════════════════════════════════════════════════════


class TestCLI:
    def test_cli_doctor(self):
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "pdbfixer" in result.output
        assert "OpenMM" in result.output
        assert "pdb2pqr" in result.output

    def test_cli_schema(self):
        result = runner.invoke(app, ["schema"])
        assert result.exit_code == 0
        assert "ProtPrepRequest" in result.output
        assert "ProtPrepResult" in result.output

    def test_cli_prepare_no_input_exits_2(self):
        result = runner.invoke(app, ["prepare"])
        assert result.exit_code == 2

    def test_cli_prepare_dry_run_with_pdb_id(self):
        result = runner.invoke(app, ["prepare", "--pdb-id", "1CRN", "--dry-run"])
        assert result.exit_code == 0
        assert "1CRN" in result.output
        assert "Dry run" in result.output

    def test_cli_prepare_dry_run_disabled_steps(self):
        result = runner.invoke(
            app,
            [
                "prepare",
                "--pdb-id",
                "1CRN",
                "--dry-run",
                "--no-energy-minimize",
                "--no-assign-protonation",
            ],
        )
        assert result.exit_code == 0
        assert "Disabled steps" in result.output
        assert "energy_minimize" in result.output
        assert "assign_protonation" in result.output

    def test_cli_prepare_dry_run_with_input_path(self):
        result = runner.invoke(
            app, ["prepare", "--input", "/tmp/fake.pdb", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "/tmp/fake.pdb" in result.output
        assert "Dry run" in result.output

    def test_cli_prepare_dry_run_custom_ph_and_chain(self):
        result = runner.invoke(
            app,
            [
                "prepare",
                "--pdb-id",
                "4HHB",
                "--dry-run",
                "--ph",
                "6.5",
                "--chain",
                "A",
            ],
        )
        assert result.exit_code == 0
        assert "6.5" in result.output
        assert "Dry run" in result.output

    def test_cli_prepare_dry_run_all_steps_disabled(self):
        result = runner.invoke(
            app,
            [
                "prepare",
                "--pdb-id",
                "1CRN",
                "--dry-run",
                "--no-add-hydrogens",
                "--no-fill-residues",
                "--no-fill-atoms",
                "--no-remove-heterogens",
                "--no-remove-water",
                "--no-replace-nonstandard",
                "--no-assign-protonation",
                "--no-energy-minimize",
            ],
        )
        assert result.exit_code == 0
        assert "Disabled steps" in result.output
        # No enabled steps
        assert "Enabled steps:" in result.output


# ═══════════════════════════════════════════════════════════════════════════════
# Tier 3: Integration Tests (require pdbfixer + network)
# ═══════════════════════════════════════════════════════════════════════════════


@requires_pdbfixer
class TestIntegration:
    @pytest.mark.asyncio
    async def test_integration_full_prepare_defaults(self, tmp_path):
        pdb_path = await _download_1crn(tmp_path)
        spec = ProtPrepSpec(inputPath=pdb_path)
        from bind_tools.protprep.runner import run_prepare

        summary = run_prepare(spec, tmp_path / "artifacts")
        assert summary["outputPath"]
        assert Path(summary["outputPath"]).exists()
        assert "stepResults" in summary
        assert len(summary["stepResults"]) > 0

    @pytest.mark.asyncio
    async def test_integration_selective_steps(self, tmp_path):
        pdb_path = await _download_1crn(tmp_path)
        spec = ProtPrepSpec(
            inputPath=pdb_path,
            steps=ProtPrepSteps(
                energyMinimize=False,
                assignProtonation=False,
            ),
        )
        from bind_tools.protprep.runner import run_prepare

        summary = run_prepare(spec, tmp_path / "artifacts")
        step_map = {s["step"]: s for s in summary["stepResults"]}
        assert step_map["energy_minimize"]["applied"] is False
        assert "Disabled" in step_map["energy_minimize"]["skippedReason"]
        assert step_map["assign_protonation"]["applied"] is False
        assert "Disabled" in step_map["assign_protonation"]["skippedReason"]

    @pytest.mark.asyncio
    async def test_integration_chain_filtering(self, tmp_path):
        pdb_path = await _download_1crn(tmp_path)
        spec = ProtPrepSpec(
            inputPath=pdb_path,
            options=ProtPrepOptions(chains=["A"]),
        )
        from bind_tools.protprep.runner import run_prepare

        summary = run_prepare(spec, tmp_path / "artifacts")
        assert summary["chainsSelected"] == ["A"]
        assert Path(summary["outputPath"]).exists()

    @pytest.mark.asyncio
    async def test_integration_output_file_is_valid_pdb(self, tmp_path):
        pdb_path = await _download_1crn(tmp_path)
        spec = ProtPrepSpec(inputPath=pdb_path)
        from bind_tools.protprep.runner import run_prepare

        summary = run_prepare(spec, tmp_path / "artifacts")
        output = Path(summary["outputPath"])
        content = output.read_text()
        assert "ATOM" in content or "HETATM" in content
        assert "END" in content

    @pytest.mark.asyncio
    async def test_integration_json_result_envelope_via_cli(self, tmp_path):
        pdb_path = await _download_1crn(tmp_path)
        json_out = str(tmp_path / "result.json")
        result = runner.invoke(
            app,
            [
                "prepare",
                "--input",
                pdb_path,
                "--json-out",
                json_out,
                "--artifacts-dir",
                str(tmp_path / "artifacts"),
                "--no-energy-minimize",
                "--no-assign-protonation",
            ],
        )
        assert result.exit_code == 0
        envelope = json.loads(Path(json_out).read_text())
        assert envelope["kind"] == "ProtPrepResult"
        assert envelope["status"] == "succeeded"
        assert "apiVersion" in envelope

    @pytest.mark.asyncio
    async def test_integration_prepare_with_pdb_id_via_runner(self, tmp_path):
        """Exercise the _fetch_pdb code path through run_prepare."""
        spec = ProtPrepSpec(
            pdbId="1CRN",
            steps=ProtPrepSteps(
                energyMinimize=False,
                assignProtonation=False,
            ),
        )
        from bind_tools.protprep.runner import run_prepare

        summary = run_prepare(spec, tmp_path / "artifacts")
        assert summary["outputPath"]
        assert Path(summary["outputPath"]).exists()

    @pytest.mark.asyncio
    async def test_integration_energy_minimize_graceful_skip(self, tmp_path):
        """If openmm is missing, energy_minimize should be skipped gracefully.
        If openmm is present, it should succeed."""
        pdb_path = await _download_1crn(tmp_path)
        spec = ProtPrepSpec(
            inputPath=pdb_path,
            steps=ProtPrepSteps(assignProtonation=False),
        )
        from bind_tools.protprep.runner import run_prepare

        summary = run_prepare(spec, tmp_path / "artifacts")
        step_map = {s["step"]: s for s in summary["stepResults"]}
        em = step_map["energy_minimize"]
        if check_openmm_installed():
            assert em["applied"] is True
        else:
            assert em["applied"] is False
            assert em["skippedReason"] is not None

    @pytest.mark.asyncio
    async def test_integration_protonation_graceful_skip(self, tmp_path):
        """If pdb2pqr is missing, protonation should be skipped gracefully.
        If pdb2pqr is present, it should succeed."""
        pdb_path = await _download_1crn(tmp_path)
        spec = ProtPrepSpec(
            inputPath=pdb_path,
            steps=ProtPrepSteps(energyMinimize=False),
        )
        from bind_tools.protprep.runner import run_prepare

        summary = run_prepare(spec, tmp_path / "artifacts")
        step_map = {s["step"]: s for s in summary["stepResults"]}
        prot = step_map["assign_protonation"]
        if check_pdb2pqr_installed():
            assert prot["applied"] is True
        else:
            assert prot["applied"] is False
            assert prot["skippedReason"] is not None
