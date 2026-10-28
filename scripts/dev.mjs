import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const windows = process.platform === 'win32';
const venv = path.join(root, '.venv', windows ? 'Scripts/python.exe' : 'bin/python');
const python = process.env.PYTHON_BIN || (existsSync(venv) ? venv : (windows ? 'python' : 'python3'));
const api = spawn(python, ['-m', 'uvicorn', 'app.main:app', '--app-dir', 'backend', '--host', '127.0.0.1', '--port', '8000'], { cwd: root, stdio: 'inherit' });
const web = spawn(windows ? 'npm.cmd' : 'npm', ['--prefix', 'frontend', 'run', 'dev', '--', ...process.argv.slice(2)], { cwd: root, stdio: 'inherit', shell: windows });
let stopping = false;
function stop(code = 0) {
  if (stopping) return;
  stopping = true;
  api.kill('SIGTERM'); web.kill('SIGTERM');
  setTimeout(() => process.exit(code), 250).unref();
}
for (const child of [api, web]) {
  child.on('error', e => { console.error(e.message); stop(1); });
  child.on('exit', code => stop(code ?? 1));
}
process.on('SIGINT', () => stop());
process.on('SIGTERM', () => stop());
