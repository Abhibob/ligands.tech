# BCR-ABL / Imatinib Validation Test Setup

## The Disease
**Chronic Myeloid Leukemia (CML)** — a blood cancer

## The Protein
**BCR-ABL kinase domain (ABL1)**
- UniProt: P00519
- PDB ID for docking: **2HYY** (ABL1 co-crystallized with imatinib — this is your gold standard)
- Alternative PDB: **1IEP** (also imatinib-bound)

## The Correct Drug (Ligand #1 — the answer)
**Imatinib (Gleevec)**
- PubChem CID: 5291
- ChEMBL ID: CHEMBL941
- SMILES: `Cc1ccc(NC(=O)c2ccc(CN3CCN(C)CC3)cc2)cc1Nc1nccc(-c2cccnc2)n1`

---

## 49 Decoy Molecules

These are real drug-like molecules from public databases (PubChem/ZINC) that have similar physical properties to imatinib (molecular weight, logP, etc.) but are structurally different and NOT known to bind BCR-ABL. This makes the test fair — the system can't cheat by just picking the biggest or most charged molecule.

**The easiest approach: Use DUD-E's pre-built ABL1 benchmark set.**

DUD-E (Directory of Useful Decoys — Enhanced) from UCSF already has a curated ABL1 dataset:
- Download URL: https://dude.docking.org/targets/abl1
- File: `abl1.tar.gz`
- Contains:
  - `actives_final.sdf.gz` — known active compounds (including imatinib)
  - `decoys_final.sdf.gz` — property-matched decoys (~11,000+)
  - `crystal_ligand.mol2` — the crystal structure ligand for reference

**For your 50-molecule test, do this:**
1. Download the abl1.tar.gz from DUD-E
2. Take imatinib as your 1 active
3. Randomly sample 49 decoys from `decoys_final.sdf.gz`
4. Shuffle them together so imatinib is in a random position
5. Feed the shuffled set to your platform

This is scientifically rigorous because DUD-E decoys are specifically designed to be challenging — they match imatinib's physical properties (molecular weight ~493, logP, rotatable bonds, hydrogen bond donors/acceptors) but have completely different chemical structures.

---

## Alternatively: Hand-Pick 49 Common Drugs as Decoys

If you want a simpler, more presentation-friendly approach, use well-known drugs that obviously aren't kinase inhibitors. This is less rigorous but easier to explain to judges:

| # | Drug | What it's for | PubChem CID | SMILES |
|---|---|---|---|---|
| 1 | **Imatinib (THE ANSWER)** | **CML (the cancer)** | **5291** | `Cc1ccc(NC(=O)c2ccc(CN3CCN(C)CC3)cc2)cc1Nc1nccc(-c2cccnc2)n1` |
| 2 | Aspirin | Pain/inflammation | 2244 | `CC(=O)Oc1ccccc1C(=O)O` |
| 3 | Metformin | Diabetes | 4091 | `CN(C)C(=N)NC(=N)N` |
| 4 | Omeprazole | Acid reflux | 4594 | `COc1ccc2[nH]c(S(=O)Cc3ncc(C)c(OC)c3C)nc2c1` |
| 5 | Lisinopril | Blood pressure | 5362119 | `NCCCC[C@@H](N[C@@H](CCc1ccccc1)C(=O)O)C(=O)N1CCCC1C(=O)O` |
| 6 | Atorvastatin | Cholesterol | 60823 | `CC(C)c1n(CC[C@@H](O)C[C@@H](O)CC(=O)O)c(-c2ccccc2)c(-c2ccc(F)cc2)c1C(=O)Nc1ccccc1` |
| 7 | Amlodipine | Blood pressure | 2162 | `CCOC(=O)C1=C(COCCN)NC(C)=C(C(=O)OC)C1c1ccccc1Cl` |
| 8 | Metoprolol | Heart rate | 4171 | `COCCc1ccc(OCC(O)CNC(C)C)cc1` |
| 9 | Sertraline | Depression | 68617 | `CN[C@H]1CC[C@@H](c2ccc(Cl)c(Cl)c2)c2ccccc21` |
| 10 | Loratadine | Allergies | 3957 | `CCOC(=O)N1CCC(=C2c3ccc(Cl)cc3CCc3cccnc32)CC1` |
| 11 | Ciprofloxacin | Bacterial infection | 2764 | `O=C(O)c1cn(C2CC2)c2cc(N3CCNCC3)c(F)cc2c1=O` |
| 12 | Fluoxetine | Depression | 3386 | `CNCCC(Oc1ccc(C(F)(F)F)cc1)c1ccccc1` |
| 13 | Ibuprofen | Pain | 3672 | `CC(C)Cc1ccc(C(C)C(=O)O)cc1` |
| 14 | Acetaminophen | Pain/fever | 1983 | `CC(=O)Nc1ccc(O)cc1` |
| 15 | Ranitidine | Stomach ulcers | 3001055 | `CNC(/N=C/[N+](=O)[O-])NCCSCc1ccc(CN(C)C)o1` |
| 16 | Warfarin | Blood thinner | 54678486 | `CC(=O)CC(c1ccccc1)c1c(O)c2ccccc2oc1=O` |
| 17 | Gabapentin | Nerve pain | 3446 | `NCC1(CC(=O)O)CCCCC1` |
| 18 | Levothyroxine | Thyroid | 5819 | `N[C@@H](Cc1cc(I)c(Oc2cc(I)c(O)c(I)c2)c(I)c1)C(=O)O` |
| 19 | Montelukast | Asthma | 5281040 | `CC(C)(O)c1ccccc1CCC(SCC1(CC(=O)O)CC1)c1cccc(/C=C/c2ccc3ccc(Cl)cc3n2)c1` |
| 20 | Tamoxifen | Breast cancer | 2733526 | `CC/C(=C(\c1ccccc1)c1ccccc1)c1ccc(OCCN(C)C)cc1` |
| 21 | Sildenafil | Erectile dysfunction | 5212 | `CCCc1nn(C)c2c1nc(nc2OCC)c1cc(ccc1OCC)S(=O)(=O)N1CCN(C)CC1` |
| 22 | Caffeine | Stimulant | 2519 | `Cn1c(=O)c2c(ncn2C)n(C)c1=O` |
| 23 | Diazepam | Anxiety | 3016 | `CN1C(=O)CN=C(c2ccccc2)c2cc(Cl)ccc21` |
| 24 | Penicillin V | Bacterial infection | 6869 | `CC1(C)[C@@H](N2C(=O)[C@@H](NC(=O)COc3ccccc3)[C@H]2S1)C(=O)O` |
| 25 | Prednisone | Inflammation | 5865 | `C[C@]12C=CC(=O)C=C1CC[C@@H]1[C@@H]2[C@@H](O)C[C@@]2(C)[C@H]1CC[C@]2(O)C(=O)CO` |
| 26 | Doxycycline | Bacterial infection | 54671203 | `C[C@@H]1c2cccc(O)c2C(=O)C2=C(O)[C@]3(O)C(=O)C(C(N)=O)=C(O)[C@@H](N(C)C)[C@@H]3[C@@H](O)[C@@H]21` |
| 27 | Naproxen | Pain/inflammation | 156391 | `COc1ccc2cc(C(C)C(=O)O)ccc2c1` |
| 28 | Clonazepam | Seizures | 2802 | `O=C1CN=C(c2ccccc2Cl)c2cc([N+](=O)[O-])ccc2N1` |
| 29 | Tramadol | Pain | 33741 | `COc1cccc(C2(O)CCCC(CN(C)C)C2)c1` |
| 30 | Hydroxychloroquine | Malaria/lupus | 3652 | `CCN(CCO)CCCC(C)Nc1ccnc2cc(Cl)ccc12` |
| 31 | Azithromycin | Bacterial infection | 447043 | `CC[C@H]1OC(=O)[C@H](C)[C@H](O[C@H]2C[C@@](C)(OC)[C@@H](O)[C@H](C)O2)[C@H](C)[C@@H](O[C@@H]2O[C@H](C)C[C@@H](N(C)C)[C@H]2O)[C@](C)(O)C[C@@H](C)C(=O)[C@H](C)[C@@H](O)[C@]1(C)O` |
| 32 | Cetirizine | Allergies | 2678 | `OC(=O)COCCN1CCN(C(c2ccccc2)c2ccc(Cl)cc2)CC1` |
| 33 | Melatonin | Sleep | 896 | `COc1ccc2[nH]cc(CCNC(C)=O)c2c1` |
| 34 | Valacyclovir | Antiviral | 60773 | `CC(C)[C@@H](N)C(=O)OCCOCn1cnc2c(=O)[nH]c(N)nc21` |
| 35 | Sumatriptan | Migraines | 5358 | `CNS(=O)(=O)Cc1ccc2[nH]cc(CCN(C)C)c2c1` |
| 36 | Esomeprazole | Acid reflux | 9579578 | `COc1ccc2[nH]c([S@@](=O)Cc3ncc(C)c(OC)c3C)nc2c1` |
| 37 | Duloxetine | Depression | 60835 | `CNCC[C@H](Oc1cccc2ccccc12)c1cccs1` |
| 38 | Rosuvastatin | Cholesterol | 446157 | `CC(C)c1nc(N(C)S(C)(=O)=O)nc(-c2ccc(F)cc2)c1/C=C/[C@@H](O)C[C@@H](O)CC(=O)O` |
| 39 | Clopidogrel | Blood thinner | 60606 | `COC(=O)[C@H](c1ccccc1Cl)N1CCc2sccc2C1` |
| 40 | Pantoprazole | Acid reflux | 4679 | `COc1ccnc(CS(=O)c2nc3cc(OC(F)F)ccc3[nH]2)c1OC` |
| 41 | Losartan | Blood pressure | 3961 | `CCCCc1nc(Cl)c(CO)n1Cc1ccc(-c2ccccc2-c2nn[nH]n2)cc1` |
| 42 | Memantine | Alzheimer's | 4054 | `CC12CC3CC(N)(C1)CC(C)(C3)C2` |
| 43 | Finasteride | Hair loss/prostate | 57363 | `CC(C)(C)NC(=O)[C@H]1CC[C@H]2[C@@H]3CC[C@H]4NC(=O)C=C[C@]4(C)[C@H]3CC[C@]12C` |
| 44 | Allopurinol | Gout | 135401907 | `O=c1[nH]cnc2[nH]ncc12` |
| 45 | Acyclovir | Antiviral | 135398513 | `Nc1nc(=O)c2ncn(COCCO)c2[nH]1` |
| 46 | Donepezil | Alzheimer's | 3152 | `COc1cc2CC(CC2=O)CC(=O)c2cc(OC)c(OC)cc21` |
| 47 | Buspirone | Anxiety | 2477 | `O=C1CC2(CCCC2)CC(=O)N1CCCCN1CCN(c2ncccn2)CC1` |
| 48 | Terbinafine | Fungal infection | 5402 | `CN(/C=C/C#CC(C)(C)C)Cc1cccc2ccccc12` |
| 49 | Riluzole | ALS | 5070 | `Nc1nc2cc(OC(F)(F)F)ccc2s1` |
| 50 | Clemastine | Allergies | 26987 | `CN1CCC[C@@H]1CCO[C@](C)(c1ccccc1)c1ccc(Cl)cc1` |

---

## How to Run the Test

1. **Protein setup:** Use PDB ID **2HYY** — but remove the co-crystallized imatinib from the structure before docking (otherwise you're cheating by giving the system the answer). Keep the protein chain only.

2. **Ligand library:** Take all 50 SMILES above, shuffle them randomly, and number them 1-50 without revealing which is imatinib.

3. **Run your platform** on this shuffled library against BCR-ABL.

4. **Check results:** See where imatinib ranks. If it's top 5, that's a great result. Top 10 out of 50 is still very strong (top 20%).

5. **Bonus visual:** Compare your predicted imatinib pose to the experimental pose from 2HYY. If the RMSD is under 2-3 Å, that's considered a successful pose prediction in the field.

---

## What to Say in the Presentation

If imatinib ranks **#1-3**: "Our system identified the FDA-approved cancer drug as the top candidate from a blind pool of 50 molecules."

If imatinib ranks **#4-5**: "Our system ranked the actual FDA-approved drug in the top 10% of candidates."

If imatinib ranks **#6-10**: "Out of 50 molecules, our system placed the real cancer drug in the top 20% — meaning a researcher would only need to test 10 compounds instead of 50 to find the right one."

Even the worst-case framing sounds impressive because you're showing the system narrows down candidates dramatically.

---

## For the DUD-E Approach (More Rigorous)

Download: https://dude.docking.org/targets/abl1

This gives you:
- ~182 known active compounds against ABL1
- ~11,000+ property-matched decoys

For a hackathon demo, randomly pick 49 decoys from the decoy set and mix in imatinib. This approach is more scientifically defensible because the decoys are specifically designed to be challenging (similar physical properties, different topology). If a judge asks "weren't those decoys just random junk?" you can say "No — we used DUD-E from UCSF, which is the standard benchmarking dataset used in the molecular docking research community."
