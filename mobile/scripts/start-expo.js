#!/usr/bin/env node

const { spawn } = require("node:child_process");
const os = require("node:os");
const path = require("node:path");

const projectRoot = path.resolve(__dirname, "..");
const expoCli = path.join(projectRoot, "node_modules", "expo", "bin", "cli");
const args = process.argv.slice(2);

function isPrivateIpv4(address) {
  if (/^10\./.test(address) || /^192\.168\./.test(address)) {
    return true;
  }

  const match = address.match(/^172\.(\d+)\./);
  return Boolean(match && Number(match[1]) >= 16 && Number(match[1]) <= 31);
}

function findLanHost() {
  for (const entries of Object.values(os.networkInterfaces())) {
    for (const entry of entries ?? []) {
      if (entry.family === "IPv4" && !entry.internal && isPrivateIpv4(entry.address)) {
        return entry.address;
      }
    }
  }

  return null;
}

function usesLanHost(argv) {
  const hostIndex = argv.indexOf("--host");
  return argv.includes("--lan") || (hostIndex >= 0 && argv[hostIndex + 1] === "lan");
}

const env = {
  ...process.env,
  EXPO_NO_DEPENDENCY_VALIDATION: "1",
};

if (usesLanHost(args) && !env.REACT_NATIVE_PACKAGER_HOSTNAME) {
  const lanHost = findLanHost();
  if (lanHost) {
    env.REACT_NATIVE_PACKAGER_HOSTNAME = lanHost;
    console.log(`Using LAN host ${lanHost}`);
  }
}

const child = spawn(process.execPath, [expoCli, ...args], {
  cwd: projectRoot,
  env,
  stdio: "inherit",
  shell: false,
});

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }

  process.exit(code ?? 0);
});
