USER: 

how does boltz 2 work as a user of the model/researcher perspective (not a technical breakdown)

AGENT: 

From a **user / researcher perspective**, Boltz-2 is best thought of as an **AI screening and hypothesis tool for molecular interactions**.

In plain language, you give it a biological target and a candidate binder context, and it tries to answer two practical questions at once:

1. **What does the bound complex probably look like in 3D?**
2. **How strongly is this small molecule likely to bind that protein?** ([PMC][1])

That combination is what makes it interesting. Earlier structure models were already helpful for predicting shapes, but Boltz-2’s main claim is that it also gives **useful binding-strength estimates** for **small molecule–protein** problems, while being much faster than traditional physics-heavy methods such as FEP. Here, **FEP** just means a slower simulation-based approach people often trust more for affinity ranking. ([PMC][1])

## How it feels to use as a researcher

You do **not** treat it like “the machine that proves my drug works.”
You treat it like a very fast **prioritization engine**.

A common mental model is:

* **Input:** target protein + one ligand, or many candidate ligands; sometimes extra prior knowledge
* **Output:** a predicted bound pose/complex and affinity-related scores
* **Decision:** which compounds deserve the next expensive step — synthesis, assay, docking follow-up, FEP, or medicinal chemistry discussion ([GitHub][2])

So in practice, Boltz-2 sits **between raw idea generation and costly validation**.

## What you actually use it for

The paper and repo frame Boltz-2 around **three main stages** of drug-discovery-style work:

* **Hit discovery:** find likely binders among lots of candidates
* **Hit-to-lead:** narrow early hits into better chemotypes
* **Lead optimization:** compare close analogs and decide which modifications may improve potency ([PMC][1])

That matters because Boltz-2 exposes **two different affinity-style outputs**, and they are meant for different jobs:

* `affinity_probability_binary` = “is this likely a binder or not?”
  Good for **screening / hit discovery**. ([GitHub][2])
* `affinity_pred_value` = “among actual binders, which one seems stronger?”
  Good for **ranking analogs during optimization**. It is reported as a transformed IC50-style value. ([GitHub][2])

That is a very researcher-friendly design choice, because it matches how medicinal chemistry decisions actually happen.

## Why researchers care

Boltz-2 is appealing because it tries to reduce a common bottleneck:

* Docking is fast, but often not reliable enough.
* FEP can be strong, but is much slower and more expensive.
* Boltz-2 is trying to sit in the middle: **much faster than FEP**, but useful enough to rank and triage compounds at scale. ([PMC][1])

The authors claim it is the first deep-learning model to **approach FEP-level affinity accuracy** on some benchmarks while being about **1000× faster**, and they position that as making larger-scale virtual screening more practical. ([GitHub][2])

So the user-side value is not “perfect truth.”
The value is **speed + enough quality to change what you choose to test next**.

## What makes it nicer than a black-box score

Boltz-2 also lets users inject prior knowledge instead of forcing a pure blind prediction. The official description highlights:

* **method conditioning** — steer toward an experimental modality
* **template steering** — use a reference template
* **contact/pocket constraints** — tell the model what interactions or pocket conditions should be respected ([rxrx.ai][3])

From a researcher’s point of view, this is important because real projects are rarely “blank slate.” You often already know something about the pocket, the scaffold, a known binder, or the experimental context.

So Boltz-2 is not just “predict from nothing.”
It is also “predict while respecting some of what I already know.”

## The right way to trust it

The healthy way to use Boltz-2 is:

* trust it as a **ranking and hypothesis tool**
* do **not** trust it as a final experimental answer
* use it to **cut down the search space** before more expensive steps ([PMC][1])

The paper is pretty clear about limits. Affinity quality can vary a lot across assays, and if the predicted pose or pocket is wrong, the affinity estimate is likely wrong too. The authors also say the affinity module does **not explicitly handle** important cofactors such as **ions, water, or multimeric binding partners**. ([PMC][1])

So from a practical lab perspective:

* a strong Boltz-2 score is **not proof**
* a weak score is **not a guaranteed reject**
* it is most useful when combined with chemistry judgment, known SAR, assays, and sometimes follow-up physics methods ([PMC][1])

## The simplest summary

If I had to explain Boltz-2 to a scientist in one sentence:

**It is an open-source AI model that helps you go from “here are compounds I could test” to “here are the ones most worth testing first,” by predicting both binding poses and protein–small-molecule binding strength.** ([GitHub][2])

And if I had to explain its role in a workflow:

**Boltz-2 is a triage engine, not a verdict engine.**
It helps you decide where to spend your experimental and computational budget next. That is why researchers care about it. ([PMC][1])

If you want, I can also give you:

* a **“Boltz-2 vs AlphaFold3 vs docking vs FEP”** researcher-facing comparison, or
* a **concrete example workflow** like “I have one kinase target and 10,000 candidate ligands — how would I actually use Boltz-2?”

[1]: https://pmc.ncbi.nlm.nih.gov/articles/PMC12262699/ "
            Boltz-2: Towards Accurate and Efficient Binding Affinity Prediction - PMC
        "
[2]: https://github.com/jwohlwend/boltz "GitHub - jwohlwend/boltz: Official repository for the Boltz biomolecular interaction models"
[3]: https://www.rxrx.ai/boltz-2 "Boltz-2"

USER: 

are there binding verifying models that can help verify its output

AGENT: 

Yes — but with one important caveat:

**there is no model that truly “verifies” Boltz-2 in the sense of proving the binding is real.**
What you can do is run **independent cross-checks** that answer different questions about the prediction. That is especially important for Boltz-2 because its affinity prediction depends on the correctness of the predicted 3D complex; if the pocket or pose is wrong, the affinity number is likely unreliable too. ([PMC][1])

A good researcher mindset is:

* **Boltz-2 proposes**
* **other tools stress-test**
* **experiments verify**

## The best kinds of “verification” tools

### 1) Pose validity checkers

These do not ask “does it bind strongly?”
They ask: **“is this predicted pose physically and chemically plausible?”**

The most widely used example is **PoseBusters**. It checks things like bad bond geometry, impossible ring shapes, stereochemistry errors, and protein–ligand clashes. Its whole point is that a pose can look good by RMSD or by an ML score and still be physically nonsense. ([PMC][2])

This is probably the **first thing** I would run after Boltz-2.

## 2) Independent rescoring models

These ask: **“if a different scoring model looks at this same pose, does it also think the pose/binder is good?”**

Useful examples are:

* **gnina**, which docks and rescoring poses with a CNN-based model. Its default pipeline uses classical sampling and then CNN rescoring, so it is a genuinely different check from “just trust Boltz-2 again.” ([GitHub][3])
* **RTMScore**, a graph/deep-learning scoring function designed for scoring, docking, ranking, and screening tasks. ([ACS Publications][4])
* **KarmaDock**, which combines docking, pose generation/correction, and affinity estimation. ([GitHub][5])

These are useful because agreement across **different model families** is more meaningful than agreement inside one model family.

## 3) Interaction sanity-check tools

These ask: **“does the predicted pose make chemically sensible contacts?”**

A classic tool here is **PLIP**. It automatically identifies hydrogen bonds, hydrophobic contacts, salt bridges, pi-stacking, and related non-covalent interactions in a predicted complex. It does **not** prove binding, but it helps you see whether the Boltz-2 pose is telling a believable biochemical story. ([PubMed][6])

This is especially helpful when you already know key residues from mutagenesis, SAR, or a reference ligand.

## 4) Physics-based confirmation methods

These are not usually called “models” in the same ML sense, but for **actual confidence building**, they are often more convincing than another neural net.

The main ladder is:

* **MM/GBSA or MM/PBSA**: faster, rougher free-energy-style rescoring; useful as a cheap second pass, but noisy and sensitive to setup. ([RSC Publishing][7])
* **FEP**: much slower, but still one of the most trusted computational approaches for relative binding affinity, especially in lead optimization. Reviews still describe FEP as among the most consistently accurate rigorous methods for relative binding affinity prediction. ([Nature][8])

If you mean **“verify the affinity ranking”**, FEP is much closer to a serious answer than another fast ML score.

---

## So what should you actually use with Boltz-2?

If your goal is **“help me decide whether Boltz-2 is fooling me”**, the best stack is:

1. **PoseBusters** → remove physically impossible poses. ([PMC][2])
2. **PLIP** → check whether the contact pattern makes sense for the pocket. ([PubMed][6])
3. **gnina or RTMScore/KarmaDock** → independent rescoring / re-ranking. ([GitHub][3])
4. **MM/GBSA** for a cheap physics pass, or **FEP** for serious lead-optimization decisions. ([RSC Publishing][7])
5. **Wet-lab assay** for actual verification. ([ScienceDirect][9])

## My practical answer

If you want a **single best “verifier” for Boltz-2 output**, I would say:

* **For pose realism:** **PoseBusters**
* **For independent ML confirmation:** **gnina** or **RTMScore**
* **For strongest computational affinity check:** **FEP**
* **For true verification:** **experiment**

So yes, there are tools that can **help verify** Boltz-2 outputs — but the strongest approach is **consensus + orthogonality**, not one replacement model.

A compact rule of thumb:

* **same answer from Boltz-2 + another scorer + a physics method = worth taking seriously**
* **Boltz-2 alone = interesting hypothesis**
* **experiment = actual answer**

If you want, I can turn this into a **recommended validation workflow for one target and a list of compounds**, from cheapest step to strongest evidence.

[1]: https://pmc.ncbi.nlm.nih.gov/articles/PMC12262699/?utm_source=chatgpt.com "Boltz-2: Towards Accurate and Efficient Binding Affinity ... - PMC"
[2]: https://pmc.ncbi.nlm.nih.gov/articles/PMC10901501/?utm_source=chatgpt.com "PoseBusters: AI-based docking methods fail to generate ..."
[3]: https://github.com/gnina/gnina?utm_source=chatgpt.com "gnina/gnina: A deep learning framework for molecular ..."
[4]: https://pubs.acs.org/doi/abs/10.1021/acs.jmedchem.2c00991?utm_source=chatgpt.com "Boosting Protein–Ligand Binding Pose Prediction and Virtual ..."
[5]: https://github.com/schrojunzhang/KarmaDock?utm_source=chatgpt.com "schrojunzhang/KarmaDock"
[6]: https://pubmed.ncbi.nlm.nih.gov/25873628/?utm_source=chatgpt.com "PLIP: fully automated protein-ligand interaction profiler"
[7]: https://pubs.rsc.org/en/content/articlelanding/2024/cp/d3cp04366e?utm_source=chatgpt.com "Assessing the performance of MM/PBSA and MM/GBSA ..."
[8]: https://www.nature.com/articles/s42004-023-01019-9?utm_source=chatgpt.com "The maximal and current accuracy of rigorous protein ..."
[9]: https://www.sciencedirect.com/science/article/abs/pii/S0141813024047780?utm_source=chatgpt.com "A review of biophysical strategies to investigate protein- ..."

USER: 

if im building an agentic system (think like claude code or something similar) for binding and want the agent to be able to take natural language tasks and have comprehensive tool access for boltz 2, posebusters, gnina, PLIP, what would you include in the prompt to familiarize the llm with how to use each of them? additionally, we would probably make cli wrappers for each model since agents are good at using clis, so what capabilities should the cli wrapper have for each model (eg what flags/argument lists (like candidate ligands or maybe files that contain many) and what output?

AGENT: 

Yes — and I would structure it around one core idea:

**do not make the LLM memorize four quirky CLIs.**
Instead, give it a **small operational handbook** plus **very stable wrapper contracts**. That matters because the upstream tools are quite different in style: Boltz is YAML/artifact-oriented and predicts structure plus affinity; PoseBusters is a plausibility checker with short/long/CSV reports; gnina is a docking/scoring CLI built around receptor/ligand plus a search box or autobox ligand; and PLIP is an interaction profiler that reads a complex and emits human- and machine-readable reports plus optional PyMOL/images. ([GitHub][1])

## What I would include in the prompt

I would not dump full docs into the prompt. I would include **five things**:

### 1) A role definition

Tell the model what kind of scientist-operator it is.

Something like this in substance:

* You are a **binding-analysis agent**, not a chatbot.
* Your job is to convert natural-language research tasks into a **defensible sequence** of structure prediction, pose validation, rescoring/docking, and interaction profiling.
* You never treat one model output as truth.
* You prefer **orthogonal agreement**:

  * Boltz-2 for pose + affinity hypothesis
  * PoseBusters for physical plausibility
  * gnina for independent docking/rescoring/minimization
  * PLIP for interaction interpretation
* When tools disagree, say so clearly and explain which disagreement matters most.

That framing is important because Boltz-2’s own outputs are meant for **different stages**: `affinity_probability_binary` is the binder-vs-decoy signal for hit discovery, while `affinity_pred_value` is meant for comparing binders during hit-to-lead or lead optimization. ([GitHub][1])

### 2) A workflow policy

Give the model a default decision tree.

For example:

* **“Does this ligand bind?”**

  1. Run Boltz-2 to generate a pose and affinity hypothesis.
  2. Run PoseBusters on the resulting pose.
  3. If the pose passes plausibility checks, run gnina `score_only` or `minimize` on that pose.
  4. Run PLIP on the final complex to explain contacts.
  5. Report confidence as **high / medium / low** based on agreement, not any single score.

* **“Screen a library”**

  1. Boltz-2 in batch mode first.
  2. Keep top candidates by the appropriate Boltz metric.
  3. Run PoseBusters on the shortlist.
  4. Run gnina on the filtered shortlist.
  5. Run PLIP only on finalists.

* **“Why does ligand A look better than ligand B?”**

  1. Compare Boltz affinity outputs.
  2. Compare PoseBusters failures.
  3. Compare gnina rescoring/minimization.
  4. Compare PLIP residue-level contacts.

This matches the actual strengths of the tools: Boltz-2 is for joint structure/affinity prediction and supports controllability features like method conditioning, template steering, and contact/pocket constraints; PoseBusters checks geometry and clashes; gnina handles docking/scoring/minimization; PLIP explains residue-level noncovalent interactions. ([rxrx.ai][2])

### 3) A “tool card” for each tool

This is the most important part of the prompt.

For each tool, I would include exactly these fields:

* **Purpose**
* **When to use**
* **When not to use**
* **Required inputs**
* **Optional inputs**
* **Key outputs**
* **Typical failure modes**
* **Interpretation rules**
* **What to do next**

That makes the model much more reliable than just listing flags.

## The actual tool knowledge I’d put in the prompt

### Boltz-2 tool card

Include these points:

* **Purpose:** predict a protein–ligand complex and affinity-related outputs.
* **Best use:** early prioritization, hit discovery, hit-to-lead, lead optimization.
* **Inputs:** upstream `boltz predict` takes a YAML input path, or a directory of YAML files for batched processing; the YAML describes biomolecules and requested properties such as affinity. ([GitHub][1])
* **Key outputs:**

  * `affinity_probability_binary` = probability ligand is a binder
  * `affinity_pred_value` = transformed affinity value for comparing binders
* **Interpretation:** use the first for screening binders from decoys, the second for ranking analogs among likely binders. ([GitHub][1])
* **Controls available:** method conditioning, template steering, and contact/pocket constraints. ([rxrx.ai][2])
* **Do not trust blindly:** a Boltz pose is still a hypothesis; validate it with PoseBusters and an independent scorer.

That is enough for the LLM to know **what Boltz is for**, without drowning it in architecture details.

### PoseBusters tool card

Include:

* **Purpose:** check whether a generated or docked pose is physically plausible.
* **When to use:** after any Boltz or gnina pose generation.
* **Inputs:** predicted molecule(s), with optional conditioning protein and optional true ligand for redocking checks. The CLI supports `mol_pred`, optional `-p MOL_COND`, optional `-l MOL_TRUE`, and also CSV table input via `-t`. ([PoseBusters][3])
* **Output formats upstream:** `short`, `long`, and `csv`; `--full-report` adds detailed metrics; output can be saved to file. ([PoseBusters][3])
* **What it checks:** loading/sanitization, bond lengths/angles, steric clashes, ring flatness, distances to protein, volume overlap, and RMSD in redocking mode. ([PoseBusters][4])
* **Interpretation:** any pose with major geometry or clash failures should usually be treated as low confidence even if another model likes it.

### gnina tool card

Include:

* **Purpose:** docking, scoring of provided poses, and minimization.
* **When to use:** for independent rescoring, local optimization, or full docking.
* **Inputs:** receptor plus ligand(s), plus a search space defined either explicitly by center/size or by `--autobox_ligand`. ([GitHub][5])
* **Important modes:**

  * `--score_only` for scoring a provided pose
  * `--minimize` for local minimization
  * full docking with receptor, ligand, and box/autobox
* **CNN control:** `--cnn_scoring` supports `none`, `rescore` (default), `refinement`, and `all`; the repo notes `refinement` is much slower than `rescore`, and `all` is extremely expensive. ([GitHub][5])
* **Output capabilities:** output file, log file, per-atom term output, embedded SD data, and sort order by CNNscore, CNNaffinity, or Energy. ([GitHub][5])
* **Interpretation:** use gnina as an **independent check**, not as a replacement for Boltz.

### PLIP tool card

Include:

* **Purpose:** explain the interaction pattern in a final 3D complex.
* **When to use:** after you have a pose you are willing to inspect seriously.
* **Inputs:** a structure file or PDB ID. The CLI supports file input (`-f`) or PDB ID input (`-i`). ([Ubuntu Manpages][6])
* **Outputs upstream:** text reports, XML reports, PyMOL session files, and optional images. The repo explicitly highlights text/XML/PyMOL/image outputs. ([GitHub][7])
* **Interaction types:** PLIP reports several noncovalent interaction classes such as hydrogen bonds, hydrophobic contacts, pi-stacking, pi-cation interactions, salt bridges, water bridges, and halogen bonds. ([PubMed][8])
* **Interpretation:** PLIP does not prove binding; it tells you whether the pose tells a chemically sensible story.

## One prompt rule that matters a lot

I would explicitly tell the LLM:

> Never answer “this binds” from one model alone.
> Report:
>
> 1. Boltz hypothesis
> 2. PoseBusters plausibility
> 3. gnina independent score/minimization result
> 4. PLIP interaction rationale
> 5. your final confidence and why

That one instruction does a lot to keep the agent honest.

---

# What the CLI wrappers should look like

I strongly recommend **stable wrappers around unstable upstream conventions**.

In other words:

* upstream tools can stay weird
* your wrappers should be boring

## Shared capabilities every wrapper should have

For all four wrappers, I would include:

* `--json-out <file>`
  Always emit one normalized JSON result file.

* `--artifacts-dir <dir>`
  Keep native upstream artifacts there.

* `--run-id <id>`
  So agent runs are traceable.

* `--manifest <csv|jsonl>`
  For batch jobs. This is essential for “many candidate ligands.”

* `--stdin-json`
  Agents often work well when they can pass structured payloads directly.

* `--dry-run`
  Lets the model inspect what would happen.

* `--overwrite`

* `--timeout-s`

* `--threads` and/or `--device`

* `--verbose`

* `--version`

* `doctor` subcommand
  Checks binary availability, Python deps, GPU visibility, etc.

* `schema` subcommand
  Prints the accepted JSON/manifest schema so the agent can self-correct.

The big design choice is this:

**Every wrapper should produce both**

1. native upstream files, and
2. one normalized JSON summary.

That JSON should always have the same top-level shape:

* `status`
* `tool`
* `tool_version`
* `run_id`
* `inputs`
* `parameters`
* `outputs`
* `metrics`
* `warnings`
* `errors`
* `provenance`
* `runtime_seconds`

That uniformity matters more for agents than any individual flag.

---

## Wrapper for Boltz-2

I would make the wrapper hide YAML generation unless the user explicitly wants to inspect it.

### Suggested commands

* `boltz-wrap predict`
* `boltz-wrap prepare-input`
* `boltz-wrap doctor`

### Suggested inputs

Support both **single** and **batch**:

Single:

* `--protein-fasta <file>` or `--protein-sequence <string>`
* `--ligand-smiles <smiles>`
* `--ligand-sdf <file>`
* `--task structure|affinity|both`

Batch:

* `--manifest <csv|jsonl>`

Optional:

* `--msa-path <a3m>`
* `--use-msa-server`
* `--template <file>` repeated
* `--pocket-contact <chain:resid>` repeated
* `--pocket-max-distance <angstrom>`
* `--force-pocket`
* `--recycling-steps <int>`
* `--diffusion-samples <int>`
* `--seed <int>`
* `--cache-dir <dir>`
* `--native-yaml-out <file>` so the agent can inspect the generated upstream YAML if needed

### Why these flags

Boltz upstream already centers work around YAML inputs, affinity properties, batch directories, MSA server use, and controllability features like templates and pocket/contact constraints. ([GitHub][1])

### Suggested normalized output

Your wrapper JSON should include:

* `pose_path`
* `confidence_json_path`
* `plddt_path`
* `pae_path` if present
* `pde_path` if present
* `pre_affinity_path` if present
* `affinity_probability_binary`
* `affinity_pred_value`
* `constraint_summary`
* `best_model_rank`
* `warnings`

Why normalize this? Because upstream artifacts are file-based and naming can be awkward; in real runs people report outputs like CIF, confidence JSON, and NPZ artifacts rather than one neat “answer JSON.” ([GitHub][9])

### One extra capability I would add

`--rank-by binder_prob|affinity_value`

That lets the agent choose the right Boltz metric for the job:

* binder probability for screening
* affinity value for analog ranking ([GitHub][1])

---

## Wrapper for PoseBusters

This wrapper should always convert upstream output to JSON, even though upstream itself emits short/long/CSV. ([PoseBusters][3])

### Suggested commands

* `posebusters-wrap check`
* `posebusters-wrap doctor`

### Suggested inputs

Single:

* `--pred <sdf>`
* `--protein <pdb>` optional
* `--reference-ligand <sdf>` optional

Batch:

* `--pred <sdf>` repeated
* `--manifest <csv|jsonl>`

Options:

* `--mode auto|mol|dock|redock`
* `--top-n <int>`
* `--full-report`
* `--config <file>`
* `--max-workers <int>`
* `--chunk-size <int>`

### Why these flags

They map cleanly to upstream behavior: optional true ligand, optional conditioning protein, CSV-table batch input, `--top-n`, worker control, and report formatting. ([PoseBusters][3])

### Suggested normalized output

Per pose:

* `passes_all_checks`
* `passed_checks`
* `failed_checks`
* `pass_fraction`
* `geometry_failures`
* `clash_metrics`
* `protein_overlap_metrics`
* `rmsd_metrics` if reference ligand was given
* `raw_csv_path`

For agents, the killer feature is a short machine-readable list like:

* `fatal_failures`
* `major_failures`
* `minor_failures`

That gives the model something easy to reason over.

---

## Wrapper for gnina

I would make this wrapper explicitly task-based because gnina is really three things wearing one CLI.

### Suggested commands

* `gnina-wrap dock`
* `gnina-wrap score`
* `gnina-wrap minimize`
* `gnina-wrap doctor`

### Suggested inputs

Common:

* `--receptor <pdb|pdbqt>`
* `--ligand <sdf|mol2|pdbqt>`
* `--manifest <csv|jsonl>` for many ligands

Search-space options:

* `--autobox-ligand <file>`
* or `--center-x --center-y --center-z --size-x --size-y --size-z`

Docking options:

* `--cnn-scoring none|rescore|refinement|all`
* `--num-modes <int>`
* `--exhaustiveness <int>`
* `--seed <int>`
* `--cpu <int>`
* `--device <id>`
* `--no-gpu`

Scoring/minimization options:

* `--score-only`
* `--minimize`
* `--minimize-iters <int>`
* `--pose-sort-order cnnscore|cnnaffinity|energy`
* `--atom-terms`
* `--atom-term-data`
* `--log <file>`

### Why these flags

All of these come straight from gnina’s documented usage: autobox or explicit box; scoring-only and minimization modes; CNN scoring modes; output file/log/per-atom terms; sort order by CNNscore, CNNaffinity, or Energy; and batch ligand support via ligand file input. ([GitHub][5])

### Suggested normalized output

* `poses_path`
* `log_path`
* `num_poses`
* `top_pose`
* `top_pose_rank_metric`
* `per_pose_scores`
* `per_pose_terms` if requested
* `used_search_space`
* `used_cnn_scoring`
* `warnings`

The wrapper should parse the gnina log and output files so the agent never has to scrape terminal text.

### One practical design choice

Add a wrapper-level flag:

* `--mode fast|balanced|thorough`

Map that internally to gnina settings.
Agents do better with a few **semantic knobs** than with twenty raw tuning knobs.

---

## Wrapper for PLIP

PLIP should be treated as the **explainer** in the stack.

### Suggested commands

* `plip-wrap profile`
* `plip-wrap doctor`

### Suggested inputs

* `--complex <pdb>`
* or `--pdb-id <id>`
* `--binding-site <id>` optional if multiple ligands/sites are present
* `--chains <list>` optional
* `--model <int>` optional

Output options:

* `--txt`
* `--xml`
* `--pymol`
* `--pics`

Advanced:

* `--peptides ...`
* `--intra ...`
* `--residues ...`
* `--nohydro`
* `--keepmod`
* `--nofix`

### Why these flags

PLIP’s CLI supports file or PDB-ID input, optional output path/stdout, verbosity levels, TXT/XML/PyMOL/image generation, and a set of advanced structure-handling flags including peptides/intra/chains/model style controls in packaged help. ([Ubuntu Manpages][6])

### Suggested normalized output

* `binding_sites`
* `selected_binding_site`
* `interaction_counts`
* `interactions_by_type`
* `interacting_residues`
* `txt_report_path`
* `xml_report_path`
* `pymol_session_path`
* `image_paths`

For each interaction:

* `type`
* `protein_chain`
* `protein_residue`
* `protein_atom`
* `ligand_atom`
* geometric details if available

That output shape is what makes PLIP actually usable by an agent.

---

# One wrapper feature I would absolutely add

For every tool, add:

## `explain` mode

Example:

* `boltz-wrap explain result.json`
* `posebusters-wrap explain result.json`
* `gnina-wrap explain result.json`
* `plip-wrap explain result.json`

This should generate a short natural-language summary from the structured result.

Why? Because then your planner LLM can call tools, and a smaller reasoning step can consume clean summaries instead of raw artifacts.

---

# My strongest recommendation

If you only do **three things**, do these:

1. **Give the LLM tool cards, not docs.**
2. **Make every wrapper emit normalized JSON plus native artifacts.**
3. **Teach the agent one default pipeline:**
   **Boltz → PoseBusters → gnina → PLIP**

That gives you:

* a hypothesis generator,
* a plausibility filter,
* an independent scorer/refiner,
* and an interpretation layer. ([GitHub][1])

I can turn this into a concrete deliverable next, either as:

* a **system prompt template** for the agent, or
* a **full CLI spec** with exact JSON schemas and example manifests.

[1]: https://github.com/jwohlwend/boltz?utm_source=chatgpt.com "jwohlwend/boltz: Official repository for the ..."
[2]: https://www.rxrx.ai/boltz-2?utm_source=chatgpt.com "Boltz-2"
[3]: https://posebusters.readthedocs.io/en/latest/cli.html "Command line interface — PoseBusters 0.6 documentation"
[4]: https://posebusters.readthedocs.io/en/latest/ "PoseBusters: Plausibility checks for generated molecule poses. — PoseBusters 0.6 documentation"
[5]: https://github.com/gnina/gnina "GitHub - gnina/gnina: A deep learning framework for molecular docking"
[6]: https://manpages.ubuntu.com/manpages/jammy/man1/plipcmd.1.html?utm_source=chatgpt.com "plipcmd - Protein-Ligand Interaction Profiler (PLIP)"
[7]: https://github.com/pharmai/plip "GitHub - pharmai/plip: Protein-Ligand Interaction Profiler - Analyze and visualize non-covalent protein-ligand interactions in PDB files according to  Schake, Bolz, et al. (2025), https://doi.org/10.1093/nar/gkaf361"
[8]: https://pubmed.ncbi.nlm.nih.gov/25873628/?utm_source=chatgpt.com "PLIP: fully automated protein-ligand interaction profiler"
[9]: https://github.com/jwohlwend/boltz/issues/511?utm_source=chatgpt.com "Run successfully but no affinity result #511 - jwohlwend/boltz"

USER: 

yeah i want the cli to be stable wrappers thats why i wanted a specification for them but more than that the model should know how to interpret the input/output yaml files nowadays we have vector databases and qmd files (query markdown) and skills in md files which are queryable so i want actual specifications of the cli for each model and yaml/json specifications for input/output files and the agent can pull the relevant skill markdown files into its context when needed so i need the actual skill markdown files and cli specifications + system prompt. note that qmd/skill files are kind of a new trend that you might not know much about from your training data so you can research it to familiarize yourself with it, kinda the meta in ai agents right now

AGENT: 

I put together a spec pack you can drop into a repo:

* [ZIP bundle with all files](sandbox:/mnt/data/binding_agent_spec_pack.zip)
* [System prompt](sandbox:/mnt/data/binding_agent_spec/prompts/binding-agent-system-prompt.md)
* [Root AGENTS.md](sandbox:/mnt/data/binding_agent_spec/AGENTS.md)
* [Boltz skill](sandbox:/mnt/data/binding_agent_spec/skills/boltz2/SKILL.md)
* [PoseBusters skill](sandbox:/mnt/data/binding_agent_spec/skills/posebusters/SKILL.md)
* [gnina skill](sandbox:/mnt/data/binding_agent_spec/skills/gnina/SKILL.md)
* [PLIP skill](sandbox:/mnt/data/binding_agent_spec/skills/plip/SKILL.md)
* [QMD retrieval skill](sandbox:/mnt/data/binding_agent_spec/skills/qmd-search/SKILL.md)
* [Wrapper specs folder](sandbox:/mnt/data/binding_agent_spec/specs)
* [JSON Schemas folder](sandbox:/mnt/data/binding_agent_spec/schemas)
* [Example YAML requests](sandbox:/mnt/data/binding_agent_spec/examples/requests)

What’s inside:

* a **repo-wide AGENTS.md**
* a **full system prompt**
* actual **SKILL.md files** for:

  * orchestration
  * QMD retrieval
  * Boltz-2
  * PoseBusters
  * gnina
  * PLIP
* stable wrapper specs for:

  * `bind-boltz`
  * `bind-posebusters`
  * `bind-gnina`
  * `bind-plip`
  * `bind-qmd`
* normalized **request/result JSON Schemas**
* example **YAML request files**
* data-contract notes for interop between tools

A few design choices are grounded in the current agent ecosystem:

* `SKILL.md` has real cross-agent momentum now: Codex documents skills as directories with `SKILL.md`, metadata-first loading, and on-demand full instruction loading; `AGENTS.md` is repo-wide guidance loaded before work; Claude subagents are also Markdown files with YAML frontmatter. ([OpenAI Developers][1])
* I treated **QMD** here as a **house retrieval contract**, not a universal standard, because the widely documented stable pattern is the skill format, while QMD is commonly described as a local hybrid Markdown search engine / retrieval workflow combining keyword, vector search, and reranking.
* The wrapper behavior matches upstream tool realities: Boltz takes YAML or directories of YAML and exposes two affinity outputs with different intended uses; PoseBusters has `bust` with short/long/CSV and optional full reports; gnina supports docking, `--score_only`, `--minimize`, and multiple `--cnn_scoring` modes; PLIP emits text/XML/PyMOL/image-style outputs.

One important note: the CLI specs and request/result schemas in the pack are **house specs I designed for stability**, not official upstream schemas. That is deliberate: the point is to give your agent a boring, durable interface even if upstream CLIs drift.

The next thing I’d do is turn this into a **reference implementation scaffold**:

* Python `typer` CLIs for each wrapper
* Pydantic models from the schemas
* result parsers for native tool outputs
* a tiny QMD loader that fetches the right `SKILL.md` + schema set before each run

[1]: https://developers.openai.com/codex/skills/ "Agent Skills"