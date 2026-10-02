const vscode = require('vscode');
const fs = require('fs');
const path = require('path');

const DEFAULT_COMMAND = 'claude --worktree';

function loadConfig(root) {
  const file = path.join(root, 'claude-grid.json');
  if (!fs.existsSync(file)) {
    return { command: DEFAULT_COMMAND, terminals: [1, 2, 3, 4].map(n => ({ name: `Claude ${n}`, folder: '.' })) };
  }
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

async function openGrid() {
  const ws = vscode.workspace.workspaceFolders;
  if (!ws) return vscode.window.showErrorMessage('Claude Grid: open a folder first.');
  const root = ws[0].uri.fsPath;

  let config;
  try {
    config = loadConfig(root);
  } catch (err) {
    return vscode.window.showErrorMessage(`Claude Grid: bad claude-grid.json: ${err.message}`);
  }

  // Groups 1-4 = top-left, top-right, bottom-left, bottom-right.
  await vscode.commands.executeCommand('workbench.action.editorLayoutTwoByTwoGrid');
  config.terminals.slice(0, 4).forEach((t, i) => {
    const term = vscode.window.createTerminal({
      name: t.name || `Claude ${i + 1}`,
      cwd: path.resolve(root, t.folder || '.'),
      location: { viewColumn: i + 1 },
    });
    term.sendText(t.command || config.command || DEFAULT_COMMAND);
    term.show();
  });
}

function activate(context) {
  context.subscriptions.push(vscode.commands.registerCommand('claudeGrid.open', openGrid));
}

module.exports = { activate };
