# Stack role: Burnish

**ASSURANCE (not the live decision path).**

The home of the beautification criteria and the tools that measure code against
them. Reads trees; proposes; never writes and never certifies itself.

| Related | Role |
|---------|------|
| [Warden](https://github.com/wking53214/Warden) | The governor of change. Burnish plugs into it as a craft. Burnish imports Warden; Warden never imports Burnish. |
| [ghost_tools](https://github.com/wking53214/ghost_tools) | Forensic observation: long functions, dead code, duplicates. Burnish does not duplicate it. |
| [SWIZZLE](https://github.com/wking53214/SWIZZLE) | Adversarial challenge. Its proofs must hold before Warden accepts a change. |
| [ASSAY](https://github.com/wking53214/ASSAY) | Specimen answer key. |

```text
Live path: Admission → OBSERVE/Keys → Locks → PERCEIVE → Decision → Conservation → Execution → Custody
Assurance: ghost_tools · Burnish · Warden · SWIZZLE · ASSAY
```

```text
CODEBASE
   │
   ▼
GHOST TOOLS   observe / find
   │
   ▼
BURNISH    review / propose   (what better means)
   │
   ▼
WARDEN       authorize / gate on the suite / transform
   │
   ▼
GHOST TOOLS   re-inspect
   │
   ▼
SWIZZLE       attack
   │
   ▼
ACCEPT / REJECT
```

See [README.md](README.md).
