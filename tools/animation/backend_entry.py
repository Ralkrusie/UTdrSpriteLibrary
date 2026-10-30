"""Two launchers share one frozen dependency tree; only utdr has a console."""
import json
from pathlib import Path
import sys

import cli
import server


if __name__ == '__main__':
    if Path(sys.executable).stem.lower() == 'utdr':
        sys.exit(cli.entry())
    try:
        server.main()
    except Exception as error:
        if '--ready-file' in sys.argv:
            Path(sys.argv[sys.argv.index('--ready-file') + 1]).write_text(json.dumps({'error': str(error)}), encoding='utf-8')
            sys.exit(1)
        raise
