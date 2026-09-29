# Portable False-Positive Review Pack

This folder is self-contained for visual review.

## Protocol for the next review batch

The junior resident and the senior pathologist (`PH`) should classify all
candidates independently before discussing them. Each reviewer must work from
a separate copy of `review_template.csv` and must not see the other reviewer's
answers until both reviews are complete.

Keep three separate files:

1. the junior resident's initial answers;
2. the senior pathologist's initial answers;
3. the consensus answers recorded after discussion.

Compare the binary label, morphology category, difficulty type, and decision
to include the case as a hard negative. Report the percentage of exact
agreement for each field and, when suitable, Cohen's kappa. Never overwrite an
initial answer with the consensus answer.

## Windows

From PowerShell:

```powershell
./run_review_windows.ps1
```

If Python packages are missing:

```powershell
python -m pip install matplotlib pillow
```

## macOS

From Terminal:

```bash
chmod +x run_review_mac.sh
./run_review_mac.sh
```

If Python packages are missing:

```bash
python3 -m pip install matplotlib pillow
```

The review updates the selected CSV in place and copies reviewed images into
`review_sorted/`. Duplicate the template before each independent review and
give each copy a reviewer-specific name.
