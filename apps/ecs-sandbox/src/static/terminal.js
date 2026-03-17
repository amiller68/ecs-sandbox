/* ecs-sandbox web terminal */
(function () {
  const form = document.getElementById("connect-form");
  const sessionInput = document.getElementById("session-id");
  const tokenInput = document.getElementById("token");
  const statusEl = document.getElementById("status");
  const container = document.getElementById("terminal-container");

  // Pre-fill from URL query params
  const params = new URLSearchParams(window.location.search);
  const urlToken = params.get("token");
  const urlSession = params.get("session");

  sessionInput.value = urlSession || crypto.randomUUID();
  if (urlToken) tokenInput.value = urlToken;

  let term = null;
  let ws = null;
  let lineBuffer = "";
  let waiting = false; // true while a command is executing

  function setStatus(text, cls) {
    statusEl.textContent = text;
    statusEl.className = cls;
  }

  function writePrompt() {
    waiting = false;
    term.write("\r\n\x1b[32m$\x1b[0m ");
  }

  function connect(sessionId, token) {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${proto}//${location.host}/web/ws/${encodeURIComponent(sessionId)}?token=${encodeURIComponent(token)}`;

    ws = new WebSocket(url);
    setStatus("connecting...", "disconnected");

    ws.onopen = function () {
      setStatus("connected", "connected");
      form.querySelector("button").disabled = true;

      term = new Terminal({
        cursorBlink: true,
        fontSize: 14,
        theme: { background: "#1e1e1e" },
        convertEol: true,
      });
      const fitAddon = new FitAddon.FitAddon();
      term.loadAddon(fitAddon);
      term.open(container);
      fitAddon.fit();
      window.addEventListener("resize", function () { fitAddon.fit(); });

      term.writeln("ecs-sandbox terminal");
      term.writeln("Session: " + sessionId);
      writePrompt();

      term.onData(function (data) {
        // Ignore all input while waiting for command output
        if (waiting) return;

        for (let i = 0; i < data.length; i++) {
          const ch = data[i];
          if (ch === "\r" || ch === "\n") {
            // Enter
            term.write("\r\n");
            const cmd = lineBuffer.trim();
            lineBuffer = "";
            if (cmd) {
              waiting = true;
              sendCommand(cmd);
            } else {
              writePrompt();
            }
          } else if (ch === "\x7f" || ch === "\b") {
            // Backspace
            if (lineBuffer.length > 0) {
              lineBuffer = lineBuffer.slice(0, -1);
              term.write("\b \b");
            }
          } else if (ch === "\x03") {
            // Ctrl-C
            lineBuffer = "";
            term.write("^C");
            writePrompt();
          } else if (ch >= " ") {
            lineBuffer += ch;
            term.write(ch);
          }
        }
      });
    };

    ws.onmessage = function (evt) {
      const msg = JSON.parse(evt.data);

      if (msg.type === "history") {
        // Replay past commands
        if (msg.events && msg.events.length > 0) {
          term.writeln("\r\n--- session history ---");
          msg.events.forEach(function (e) {
            if (e.payload) {
              const payload = typeof e.payload === "string" ? JSON.parse(e.payload) : e.payload;
              term.writeln("\x1b[90m$ " + (payload.cmd || "") + "\x1b[0m");
            }
            if (e.result) {
              const result = typeof e.result === "string" ? JSON.parse(e.result) : e.result;
              if (result.stdout) term.write(result.stdout);
              if (result.stderr) term.write("\x1b[31m" + result.stderr + "\x1b[0m");
            }
          });
          term.writeln("--- end history ---");
          writePrompt();
        }
      } else if (msg.type === "output") {
        if (msg.stdout) term.write(msg.stdout);
        if (msg.stderr) term.write("\x1b[31m" + msg.stderr + "\x1b[0m");
        if (msg.exit_code !== undefined && msg.exit_code !== 0) {
          term.write("\x1b[90m[exit " + msg.exit_code + "]\x1b[0m");
        }
        writePrompt();
      } else if (msg.type === "error") {
        term.writeln("\x1b[31m" + (msg.message || "error") + "\x1b[0m");
        writePrompt();
      } else if (msg.type === "session_created") {
        term.writeln("\x1b[32mSession created.\x1b[0m");
        writePrompt();
      }
    };

    ws.onclose = function () {
      setStatus("disconnected", "disconnected");
      form.querySelector("button").disabled = false;
      waiting = false;
      if (term) term.writeln("\r\n\x1b[31m[disconnected]\x1b[0m");
    };

    ws.onerror = function () {
      setStatus("error", "error");
    };
  }

  function sendCommand(cmd) {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ cmd: cmd }));
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    const sessionId = sessionInput.value.trim();
    const token = tokenInput.value.trim();
    if (!sessionId || !token) return;
    connect(sessionId, token);
  });

  // Auto-connect when both token and session are provided via URL
  if (urlToken && urlSession) {
    connect(urlSession, urlToken);
  }
})();
