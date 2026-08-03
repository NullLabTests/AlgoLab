# Install Into Your Existing AlgoLaB Folder

From a terminal:

```bash
cd /home/illy/AlgoLaB
unzip -o AlgoLab-v1-Master-Spec.zip -d master
cd master/AlgoLab-v1-Master-Spec
opencode .
```

Then paste the full contents of `OPENCODE_KICKOFF_PROMPT.md` into OpenCode.

Keep the earlier `spec/AI-Algorithm-Discovery-Lab-Spec/` folder. It is useful
history, but the new `MASTER_SPEC.md` is canonical.

Do not ask OpenCode to build everything. The kickoff deliberately implements
Milestone M0 only, producing a tested foundation before any autonomous research
loop is enabled.
