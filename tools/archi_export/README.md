**ArchiMate XML → PNG exporter**

- **Purpose:** Automate conversion of ArchiMate model/diagram XML files to PNG.
- **Default behavior:** If `archi_command_template` in `config.json` is empty, the exporter creates placeholder PNGs (useful for CI or quick previews).
- **Full rendering:** Install Archi (or your preferred ArchiMate tool) and set `archi_command_template` in `tools/archi_export/config.json` to a working command that accepts `{input}` and `{output}` placeholders.

Example `config.json` entry:

```
{
  "archi_command_template": "C:\\Program Files\\Archi\\Archi.exe -nosplash -application com.archimatetool.commandline -model \"{input}\" -export \"{output}\""
}
```

Usage:

From repository root run:

```powershell
python scripts/export_archimate.py --source model --outdir exported_diagrams
```

Or on Windows with the wrapper:

```powershell
.\scripts\export-archimate.ps1 -Source model -OutDir exported_diagrams
```

If you want to only preview the commands (do not execute), use `--dry-run`.
