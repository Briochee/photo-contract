const { app, BrowserWindow, dialog } = require('electron')
const { spawn } = require('node:child_process')
const net = require('node:net')
const path = require('node:path')
const { existsSync, mkdirSync, readFileSync } = require('node:fs')
const { pathToFileURL } = require('node:url')

const PROJECT_ROOT = path.resolve(__dirname, '../..')
const APP_ROOT = app.isPackaged ? app.getAppPath() : path.join(PROJECT_ROOT, 'frontend')
const STARTUP_TIMEOUT_MS = 45_000
const BACKEND_SCRIPT = path.join(PROJECT_ROOT, 'scripts', 'electron_backend.py')
const BACKEND_EXECUTABLE = path.join(
  process.resourcesPath,
  'backend',
  'photography-document-studio-backend',
  'photography-document-studio-backend',
)
const STARTUP_PAGE = path.join(__dirname, 'loading.html')
const STARTUP_PAGE_URL = pathToFileURL(STARTUP_PAGE).href
const COMPATIBLE_USER_DATA_DIRECTORY = 'Photography Document Studio'

let backendProcess
let mainWindow
let backendOrigin
let backendOutputTail = ''
let quitAfterBackendStops = false
let shutdownStarted = false

app.setName('Contract Studio')

if (!app.requestSingleInstanceLock()) {
  app.quit()
} else {
  app.on('second-instance', () => {
    if (!mainWindow) return
    if (mainWindow.isMinimized()) mainWindow.restore()
    mainWindow.focus()
  })

  app.whenReady().then(startApplication).catch(showStartupError)
}

async function startApplication() {
  preserveExistingUserDataPath()

  const frontendIndex = path.join(APP_ROOT, 'dist', 'index.html')
  if (!existsSync(frontendIndex)) {
    throw new Error('The application interface is missing. Rebuild or reinstall the application.')
  }

  mainWindow = createMainWindow()
  await mainWindow.loadFile(STARTUP_PAGE)
  await updateStartupStatus(
    'Starting your local workspace',
    'Preparing the documents and records stored on this Mac.',
  )

  const port = await findAvailablePort()
  backendOrigin = `http://127.0.0.1:${port}`
  await updateStartupStatus(
    'Starting document services',
    'Checking your saved work and preparing the local database.',
  )
  backendProcess = launchBackend(port)
  await waitForBackend(backendProcess, backendOrigin)
  if (process.env.PHOTO_STUDIO_ELECTRON_DEBUG === '1') {
    console.info(`Electron-managed backend ready at ${backendOrigin}`)
  }

  backendProcess.once('exit', (code, signal) => {
    if (shutdownStarted || quitAfterBackendStops) return
    console.error(`Local backend stopped unexpectedly (code=${code}, signal=${signal}).`)
    dialog.showErrorBox(
      'Contract Studio stopped',
      'The local application backend stopped unexpectedly. Restart the desktop app to continue.',
    )
    app.quit()
  })

  await updateStartupStatus(
    'Opening your workspace',
    'Loading your clients, bookings, invoices, and documents.',
  )
  await mainWindow.loadURL(backendOrigin)
  if (process.env.PHOTO_STUDIO_ELECTRON_DEBUG === '1') {
    console.info('Desktop window loaded.')
  }
}

function preserveExistingUserDataPath() {
  const compatiblePath = path.join(app.getPath('appData'), COMPATIBLE_USER_DATA_DIRECTORY)
  mkdirSync(compatiblePath, { recursive: true })
  app.setPath('userData', compatiblePath)
}

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 960,
    minWidth: 960,
    minHeight: 680,
    show: false,
    backgroundColor: '#f1f2ef',
    title: 'Contract Studio',
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      plugins: true,
      sandbox: true,
    },
  })

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    let previewOrigin
    try {
      previewOrigin = new URL(url).origin
    } catch {
      return { action: 'deny' }
    }
    if (!url.startsWith('blob:') || previewOrigin !== backendOrigin) {
      return { action: 'deny' }
    }
    return {
      action: 'allow',
      overrideBrowserWindowOptions: {
        width: 1100,
        height: 900,
        webPreferences: {
          plugins: true,
          contextIsolation: true,
          nodeIntegration: false,
          sandbox: true,
        },
      },
    }
  })
  mainWindow.webContents.on('will-navigate', (event, targetUrl) => {
    if (targetUrl === STARTUP_PAGE_URL) return
    try {
      if (backendOrigin && new URL(targetUrl).origin === backendOrigin) return
    } catch {
      // Malformed and non-HTTP destinations are not trusted application origins.
    }
    event.preventDefault()
  })
  mainWindow.once('ready-to-show', () => mainWindow?.show())
  mainWindow.on('closed', () => {
    mainWindow = undefined
  })
  return mainWindow
}

async function updateStartupStatus(title, detail) {
  if (!mainWindow || mainWindow.isDestroyed() || mainWindow.webContents.isDestroyed()) {
    return
  }
  const script = `window.setStartupStatus(${JSON.stringify(title)}, ${JSON.stringify(detail)});`
  await mainWindow.webContents.executeJavaScript(script)
}

function pythonCommand() {
  if (app.isPackaged) {
    if (!existsSync(BACKEND_EXECUTABLE)) {
      throw new Error('The bundled local backend is missing from this app.')
    }
    return { command: BACKEND_EXECUTABLE, args: [] }
  }

  const configured = process.env.PHOTO_STUDIO_PYTHON
  if (configured) {
    if (path.isAbsolute(configured) && !existsSync(configured)) {
      throw new Error('PHOTO_STUDIO_PYTHON points to a Python executable that does not exist.')
    }
    return { command: configured, args: [] }
  }

  const localCandidates =
    process.platform === 'win32'
      ? [path.join(PROJECT_ROOT, '.venv', 'Scripts', 'python.exe')]
      : [path.join(PROJECT_ROOT, '.venv', 'bin', 'python')]
  const localPython = localCandidates.find(existsSync)
  if (localPython) return { command: localPython, args: [] }

  return {
    command: process.platform === 'win32' ? 'python' : 'python3',
    args: [],
  }
}

function packagedLegacyDataDirectory() {
  if (!app.isPackaged) return ''
  const configurationPath = path.join(process.resourcesPath, 'legacy_data_dir.txt')
  try {
    const source = readFileSync(configurationPath, 'utf8').trim()
    return path.isAbsolute(source) ? source : ''
  } catch {
    return ''
  }
}

function launchBackend(port) {
  const python = pythonCommand()
  const args = app.isPackaged ? [...python.args] : [...python.args, BACKEND_SCRIPT]
  const appEnvironment = app.isPackaged
    ? {
        PHOTO_STUDIO_DATA_DIR:
          process.env.PHOTO_STUDIO_DATA_DIR || path.join(app.getPath('userData'), 'data'),
        PLAYWRIGHT_BROWSERS_PATH: path.join(process.resourcesPath, 'playwright'),
        PHOTO_STUDIO_LEGACY_DATA_DIR: packagedLegacyDataDirectory(),
      }
    : {}
  const child = spawn(python.command, [...args, '--host', '127.0.0.1', '--port', String(port)], {
    cwd: app.isPackaged ? app.getPath('userData') : PROJECT_ROOT,
    env: {
      ...process.env,
      ...appEnvironment,
      PHOTO_STUDIO_PORT: String(port),
      PYTHONUNBUFFERED: '1',
    },
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
  })

  child.stdout.on('data', writeBackendOutput)
  child.stderr.on('data', writeBackendOutput)
  child.on('error', (error) => {
    console.error(`Could not launch the local backend: ${error.message}`)
  })
  return child
}

function writeBackendOutput(chunk) {
  backendOutputTail = `${backendOutputTail}${chunk.toString()}`.slice(-4_000)
  if (process.env.PHOTO_STUDIO_ELECTRON_DEBUG === '1') {
    process.stdout.write(`[backend] ${chunk.toString()}`)
  }
}

function findAvailablePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer()
    server.once('error', reject)
    server.listen(0, '127.0.0.1', () => {
      const address = server.address()
      if (!address || typeof address === 'string') {
        server.close()
        reject(new Error('Could not reserve a local application port.'))
        return
      }
      server.close((error) => (error ? reject(error) : resolve(address.port)))
    })
  })
}

function waitForBackend(child, origin) {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + STARTUP_TIMEOUT_MS
    let settled = false
    let retryTimer

    const finish = (error) => {
      if (settled) return
      settled = true
      clearTimeout(retryTimer)
      child.off('exit', onExit)
      child.off('error', onError)
      if (error) reject(error)
      else resolve()
    }

    const onExit = (code, signal) => {
      finish(
        new Error(
          `The local backend exited before becoming ready (code=${code}, signal=${signal}).`,
        ),
      )
    }
    const onError = (error) =>
      finish(new Error(`Could not start the local backend: ${error.message}`))

    child.once('exit', onExit)
    child.once('error', onError)

    const checkHealth = async () => {
      if (settled) return
      try {
        const response = await fetch(`${origin}/health`, {
          signal: AbortSignal.timeout(1_000),
        })
        if (response.ok) {
          finish()
          return
        }
      } catch {
        // The server can refuse connections while migrations and startup are still running.
      }

      if (Date.now() >= deadline) {
        finish(new Error('The local backend did not become ready within 45 seconds.'))
        return
      }
      retryTimer = setTimeout(checkHealth, 250)
    }

    void checkHealth()
  })
}

async function showStartupError(error) {
  console.error(error)
  if (backendProcess && backendProcess.exitCode === null) await stopBackend()
  const backendDetails = backendOutputTail.trim()
  const startupDetails = backendDetails
    ? `${error.message}\n\nBackend startup output:\n${backendDetails}`
    : error.message
  dialog.showErrorBox(
    'Could not start Contract Studio',
    app.isPackaged
      ? `${startupDetails}\n\nTry reinstalling the application. Your saved data is kept separately on this Mac.`
      : `${startupDetails}\n\nConfirm that the project Python environment is installed. See docs/SETUP.md for setup instructions.`,
  )
  app.quit()
}

function stopBackend() {
  if (!backendProcess || backendProcess.exitCode !== null || backendProcess.signalCode !== null) {
    return Promise.resolve()
  }

  return new Promise((resolve) => {
    let finished = false
    const finish = () => {
      if (finished) return
      finished = true
      clearTimeout(forceStopTimer)
      backendProcess.off('exit', finish)
      resolve()
    }
    const forceStopTimer = setTimeout(() => {
      backendProcess.kill()
      finish()
    }, 5_000)
    backendProcess.once('exit', finish)
    backendProcess.kill('SIGTERM')
  })
}

app.on('before-quit', (event) => {
  if (quitAfterBackendStops || !backendProcess || backendProcess.exitCode !== null) return
  event.preventDefault()
  if (shutdownStarted) return
  shutdownStarted = true
  void stopBackend().finally(() => {
    quitAfterBackendStops = true
    app.quit()
  })
})

app.on('window-all-closed', () => app.quit())

process.on('exit', () => {
  if (backendProcess && backendProcess.exitCode === null) backendProcess.kill()
})
