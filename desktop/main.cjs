const { app, BrowserWindow, dialog } = require("electron");
const { spawn } = require("node:child_process");
const net = require("node:net");
const path = require("node:path");
const { existsSync } = require("node:fs");

const PROJECT_ROOT = path.resolve(__dirname, "..");
const STARTUP_TIMEOUT_MS = 45_000;
const BACKEND_SCRIPT = path.join(
  PROJECT_ROOT,
  "scripts",
  "electron_backend.py",
);

let backendProcess;
let mainWindow;
let backendOrigin;
let quitAfterBackendStops = false;
let shutdownStarted = false;

app.setName("Photography Document Studio");

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (!mainWindow) return;
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.focus();
  });

  app.whenReady().then(startApplication).catch(showStartupError);
}

async function startApplication() {
  const frontendIndex = path.join(
    PROJECT_ROOT,
    "frontend",
    "dist",
    "index.html",
  );
  if (!existsSync(frontendIndex)) {
    throw new Error(
      "The frontend build is missing. Run `npm run desktop` from frontend/.",
    );
  }

  const port = await findAvailablePort();
  backendOrigin = `http://127.0.0.1:${port}`;
  backendProcess = launchBackend(port);
  await waitForBackend(backendProcess, backendOrigin);
  if (process.env.PHOTO_STUDIO_ELECTRON_DEBUG === "1") {
    console.info(`Electron-managed backend ready at ${backendOrigin}`);
  }

  backendProcess.once("exit", (code, signal) => {
    if (shutdownStarted || quitAfterBackendStops) return;
    console.error(
      `Local backend stopped unexpectedly (code=${code}, signal=${signal}).`,
    );
    dialog.showErrorBox(
      "Photography Document Studio stopped",
      "The local application backend stopped unexpectedly. Restart the desktop app to continue.",
    );
    app.quit();
  });

  mainWindow = new BrowserWindow({
    width: 1440,
    height: 960,
    minWidth: 960,
    minHeight: 680,
    backgroundColor: "#f1f2ef",
    title: "Photography Document Studio",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  mainWindow.webContents.on("will-navigate", (event, targetUrl) => {
    if (new URL(targetUrl).origin !== backendOrigin) event.preventDefault();
  });
  mainWindow.on("closed", () => {
    mainWindow = undefined;
  });

  await mainWindow.loadURL(backendOrigin);
  if (process.env.PHOTO_STUDIO_ELECTRON_DEBUG === "1") {
    console.info("Desktop window loaded.");
  }
}

function pythonCommand() {
  const configured = process.env.PHOTO_STUDIO_PYTHON;
  if (configured) {
    if (path.isAbsolute(configured) && !existsSync(configured)) {
      throw new Error(
        "PHOTO_STUDIO_PYTHON points to a Python executable that does not exist.",
      );
    }
    return { command: configured, args: [] };
  }

  const localCandidates =
    process.platform === "win32"
      ? [path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe")]
      : [path.join(PROJECT_ROOT, ".venv", "bin", "python")];
  const localPython = localCandidates.find(existsSync);
  if (localPython) return { command: localPython, args: [] };

  return {
    command: process.platform === "win32" ? "python" : "python3",
    args: [],
  };
}

function launchBackend(port) {
  const python = pythonCommand();
  const child = spawn(
    python.command,
    [
      ...python.args,
      BACKEND_SCRIPT,
      "--host",
      "127.0.0.1",
      "--port",
      String(port),
    ],
    {
      cwd: PROJECT_ROOT,
      env: {
        ...process.env,
        PHOTO_STUDIO_PORT: String(port),
        PYTHONUNBUFFERED: "1",
      },
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true,
    },
  );

  child.stdout.on("data", writeBackendOutput);
  child.stderr.on("data", writeBackendOutput);
  child.on("error", (error) => {
    console.error(`Could not launch the local backend: ${error.message}`);
  });
  return child;
}

function writeBackendOutput(chunk) {
  if (process.env.PHOTO_STUDIO_ELECTRON_DEBUG === "1") {
    process.stdout.write(`[backend] ${chunk.toString()}`);
  }
}

function findAvailablePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      if (!address || typeof address === "string") {
        server.close();
        reject(new Error("Could not reserve a local application port."));
        return;
      }
      server.close((error) => (error ? reject(error) : resolve(address.port)));
    });
  });
}

function waitForBackend(child, origin) {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + STARTUP_TIMEOUT_MS;
    let settled = false;
    let retryTimer;

    const finish = (error) => {
      if (settled) return;
      settled = true;
      clearTimeout(retryTimer);
      child.off("exit", onExit);
      child.off("error", onError);
      error ? reject(error) : resolve();
    };

    const onExit = (code, signal) => {
      finish(
        new Error(
          `The local backend exited before becoming ready (code=${code}, signal=${signal}).`,
        ),
      );
    };
    const onError = (error) =>
      finish(new Error(`Could not start the local backend: ${error.message}`));

    child.once("exit", onExit);
    child.once("error", onError);

    const checkHealth = async () => {
      if (settled) return;
      try {
        const response = await fetch(`${origin}/health`, {
          signal: AbortSignal.timeout(1_000),
        });
        if (response.ok) {
          finish();
          return;
        }
      } catch {
        // The server can refuse connections while migrations and startup are still running.
      }

      if (Date.now() >= deadline) {
        finish(
          new Error(
            "The local backend did not become ready within 45 seconds.",
          ),
        );
        return;
      }
      retryTimer = setTimeout(checkHealth, 250);
    };

    void checkHealth();
  });
}

async function showStartupError(error) {
  console.error(error);
  if (backendProcess && backendProcess.exitCode === null) await stopBackend();
  dialog.showErrorBox(
    "Could not start Photography Document Studio",
    `${error.message}\n\nConfirm that the project Python environment is installed. See docs/SETUP.md for setup instructions.`,
  );
  app.quit();
}

function stopBackend() {
  if (
    !backendProcess ||
    backendProcess.exitCode !== null ||
    backendProcess.signalCode !== null
  ) {
    return Promise.resolve();
  }

  return new Promise((resolve) => {
    let finished = false;
    const finish = () => {
      if (finished) return;
      finished = true;
      clearTimeout(forceStopTimer);
      backendProcess.off("exit", finish);
      resolve();
    };
    const forceStopTimer = setTimeout(() => {
      backendProcess.kill();
      finish();
    }, 5_000);
    backendProcess.once("exit", finish);
    backendProcess.kill("SIGTERM");
  });
}

app.on("before-quit", (event) => {
  if (
    quitAfterBackendStops ||
    !backendProcess ||
    backendProcess.exitCode !== null
  )
    return;
  event.preventDefault();
  if (shutdownStarted) return;
  shutdownStarted = true;
  void stopBackend().finally(() => {
    quitAfterBackendStops = true;
    app.quit();
  });
});

app.on("window-all-closed", () => app.quit());

process.on("exit", () => {
  if (backendProcess && backendProcess.exitCode === null) backendProcess.kill();
});
