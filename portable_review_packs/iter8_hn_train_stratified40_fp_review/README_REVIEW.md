# Portable False-Positive Review Pack

This folder is self-contained for visual review.

## Independent-review protocol

For the next review batch, the junior resident and the senior pathologist
(`PH`) must classify the candidates independently before comparing answers.
Use `review_junior.csv` and `review_ph.csv` independently; do not show either
reviewer the other person's answers until both files are complete.

After both reviews are frozen, compare the binary label, morphology category,
difficulty type, and hard-negative inclusion decision. Preserve the two
initial answers and record the post-discussion consensus in a third file. The
analysis should report the percentage of exact agreement and, when suitable,
Cohen's kappa. Do not replace an initial answer with the consensus answer.

For the later joint review, the consensus launcher displays the junior's
already-frozen answer in the window title. It reads `review_junior.csv`
without modifying it and writes the joint decision only to
`review_consensus.csv`.

## Windows

The recommended launchers do not require changing the PowerShell execution
policy. From PowerShell or Command Prompt:

```powershell
./run_review_junior_windows.cmd
# or, on the PH's independent copy:
./run_review_ph_windows.cmd
# or, for the joint review with junior answers visible:
./run_review_consensus_with_junior_windows.cmd
```

If Python packages are missing:

```powershell
python -m pip install matplotlib pillow
```

## macOS

From Terminal:

```bash
chmod +x run_review_mac.sh
chmod +x run_review_junior_mac.sh run_review_ph_mac.sh
./run_review_junior_mac.sh
# or, on the PH's independent copy:
./run_review_ph_mac.sh
# or, for the joint review with junior answers visible:
./run_review_consensus_with_junior_mac.sh
```

If Python packages are missing:

```bash
python3 -m pip install matplotlib pillow
```

The review updates the selected reviewer CSV in place and copies reviewed
images into its reviewer-specific `review_sorted_*` folder. Keep
`review_consensus.csv` blank until both independent reviews have been frozen
and the disagreement discussion begins. `review_template.csv` is an untouched
master copy.
