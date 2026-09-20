#!/usr/bin/env python3
"""Apply a reviewed SQL load atomically after verifying its downloaded archive.

Requires authenticated Supabase CLI and Docker. Temporary connection credentials
stay in memory and are passed to the disposable PostgreSQL client by environment.
"""
import argparse
import os
from pathlib import Path
import shlex
import subprocess

from prepare_source_staging import verify

CLI = ['npx', '--yes', 'supabase@2.117.0']
FIELDS = {'PGHOST', 'PGPORT', 'PGUSER', 'PGPASSWORD', 'PGDATABASE'}


def connection_environment(script, project_ref):
    values = {}
    for line in script.splitlines():
        if line.startswith('export '):
            tokens = shlex.split(line)
            if len(tokens) == 2 and '=' in tokens[1]:
                key, value = tokens[1].split('=', 1)
                if key in FIELDS:
                    values[key] = value
    if set(values) != FIELDS or not all(values.values()):
        raise ValueError('CLI did not supply a complete database connection')
    if not project_ref or project_ref not in values['PGHOST'] + values['PGUSER']:
        raise ValueError('Database connection does not match the requested project')
    return {**values, 'PGSSLMODE': 'require'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', required=True, type=Path)
    parser.add_argument('--download', required=True, type=Path)
    parser.add_argument('--project-ref', required=True)
    args = parser.parse_args()
    verified = verify(args.prepared, args.download)
    sql = (args.prepared / 'load.sql').read_bytes()
    connection = subprocess.run(
        CLI + ['db', 'dump', '--linked', '--dry-run', '--agent', 'no',
               '--output-format', 'text'], capture_output=True, text=True)
    if connection.returncode:
        raise SystemExit('Could not obtain a temporary CLI database connection; check sign-in and project linking')
    values = connection_environment(connection.stdout, args.project_ref)
    command = ['docker', 'run', '--rm', '--interactive', '--platform', 'linux/amd64']
    for key in values:
        command += ['--env', key]
    command += ['postgis/postgis:17-3.5', 'psql', '-X', '-q', '-v', 'ON_ERROR_STOP=1', '-f', '-']
    result = subprocess.run(command, env={**os.environ, **values},
                            input=b'SET ROLE postgres;\n' + sql, capture_output=True)
    if result.returncode:
        # Do not echo SQL or connection output; either may contain private data.
        raise SystemExit('Database load failed; connection closed and any uncommitted transaction rolled back')
    print(f"Verified {verified['verified_objects']} archive objects; database load committed successfully")


if __name__ == '__main__':
    main()
