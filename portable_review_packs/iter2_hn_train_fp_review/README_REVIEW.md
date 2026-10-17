# Portable False-Positive Review Pack

This folder is self-contained for visual review.

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

The review updates `review_template.csv` in place and copies reviewed images
into `review_sorted/`.
