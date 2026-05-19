# JARVIS E2E Suite Summary

- Started: `2026-05-15T15:53:04.664Z`
- Finished: `2026-05-15T15:57:14.537Z`
- Base URL: `http://127.0.0.1:8787`

## Totals

- Passed: **1**
- Failed: **32**
- Warned: **0**
- Skipped: **0**

## Batteries

### platform

- Exit code: `1`
- Passed: **1**
- Failed: **9**
- Warned: **0**
- Skipped: **0**
- Report: [/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-platform-report.json](/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-platform-report.json)

### provider-layer

- Exit code: `1`
- Passed: **0**
- Failed: **1**
- Warned: **0**
- Skipped: **0**
- Report: [/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-provider-layer-report.json](/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-provider-layer-report.json)

### full-system

- Exit code: `1`
- Passed: **0**
- Failed: **10**
- Warned: **0**
- Skipped: **0**
- Report: [/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-full-system-report.json](/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-full-system-report.json)

### workbench

- Exit code: `1`
- Passed: **0**
- Failed: **1**
- Warned: **0**
- Skipped: **0**
- Report: [/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-workbench-report.json](/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-workbench-report.json)

### identity-admin

- Exit code: `1`
- Passed: **0**
- Failed: **1**
- Warned: **0**
- Skipped: **0**
- Report: [/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-identity-admin-report.json](/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-identity-admin-report.json)

### memory-governance

- Exit code: `1`
- Passed: **0**
- Failed: **5**
- Warned: **0**
- Skipped: **0**
- Report: [/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-memory-governance-report.json](/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-memory-governance-report.json)

### approval-queue

- Exit code: `1`
- Passed: **0**
- Failed: **5**
- Warned: **0**
- Skipped: **0**
- Report: [/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-approval-queue-report.json](/Users/chris/Desktop/CODE/JARVIS/artifacts/qa/jarvis-approval-queue-report.json)

## Failures

### platform

- Exit code: `1`
- Stdout tail:
```text
},
    {
      "name": "Catalyst workspace opens as modal app",
      "error": "page.click: Timeout 30000ms exceeded.\nCall log:\n\u001b[2m  - waiting for locator('#close-modal')\u001b[22m\n\n    at /Users/chris/Desktop/CODE/JARVIS/tests/e2e/jarvis-platform.e2e.cjs:195:16\n    at check (/Users/chris/Desktop/CODE/JARVIS/tests/e2e/jarvis-platform.e2e.cjs:62:13)\n    at run (/Users/chris/Desktop/CODE/JARVIS/tests/e2e/jarvis-platform.e2e.cjs:194:9)"
    },
    {
      "name": "Modal state hides packet rail and shrinks core",
      "error": "locator.boundingBox: Timeout 30000ms exceeded.\nCall log:\n\u001b[2m  - waiting for locator('#packet-strip-toggle')\u001b[22m\n\n    at /Users/chris/Desktop/CODE/JARVIS/tests/e2e/jarvis-platform.e2e.cjs:214:72\n    at check (/Users/chris/Desktop/CODE/JARVIS/tests/e2e/jarvis-platform.e2e.cjs:62:13)\n    at run (/Users/chris/Desktop/CODE/JARVIS/tests/e2e/jarvis-platform.e2e.cjs:213:9)"
    },
    {
      "name": "Talk button remains interactive",
      "error": "page.click: Timeout 30000ms exceeded.\nCall log:\n\u001b[2m  - waiting for locator('#close-modal')\u001b[22m\n\n    at /Users/chris/Desktop/CODE/JARVIS/tests/e2e/jarvis-platform.e2e.cjs:223:16\n    at check (/Users/chris/Desktop/CODE/JARVIS/tests/e2e/jarvis-platform.e2e.cjs:62:13)\n    at run (/Users/chris/Desktop/CODE/JARVIS/tests/e2e/jarvis-platform.e2e.cjs:222:9)"
    }
  ],
  "summary": {
    "passed": 1,
    "failed": 9
  },
  "finished_at": "2026-05-15T15:56:56.157Z"
}
```

### provider-layer

- Exit code: `1`
- Stderr tail:
```text
[TypeError: fetch failed] {
  [cause]: Error: connect ECONNREFUSED 127.0.0.1:8787
      at TCPConnectWrap.afterConnect [as oncomplete] (node:net:1645:16) {
    errno: -61,
    code: 'ECONNREFUSED',
    syscall: 'connect',
    address: '127.0.0.1',
    port: 8787
  }
}
```

### full-system

- Exit code: `1`
- Stderr tail:
```text
[jarvis-full-system] fail: Operational platform endpoints have expected shape
[jarvis-full-system] start: Cognitive platform endpoints have expected shape
[jarvis-full-system] fail: Cognitive platform endpoints have expected shape
[jarvis-full-system] start: First Light and persona APIs respond
[jarvis-full-system] fail: First Light and persona APIs respond
[jarvis-full-system] start: Assistant background autonomy run responds
[jarvis-full-system] fail: Assistant background autonomy run responds
[jarvis-full-system] start: TTS endpoint returns downloadable audio
[jarvis-full-system] fail: TTS endpoint returns downloadable audio
[TypeError: fetch failed] {
  [cause]: Error: connect ECONNREFUSED 127.0.0.1:8787
      at TCPConnectWrap.afterConnect [as oncomplete] (node:net:1645:16) {
    errno: -61,
    code: 'ECONNREFUSED',
    syscall: 'connect',
    address: '127.0.0.1',
    port: 8787
  }
}
```

### workbench

- Exit code: `1`
- Stderr tail:
```text
[TypeError: fetch failed] {
  [cause]: Error: connect ECONNREFUSED 127.0.0.1:8787
      at TCPConnectWrap.afterConnect [as oncomplete] (node:net:1645:16) {
    errno: -61,
    code: 'ECONNREFUSED',
    syscall: 'connect',
    address: '127.0.0.1',
    port: 8787
  }
}
```

### identity-admin

- Exit code: `1`
- Stderr tail:
```text
[TypeError: fetch failed] {
  [cause]: Error: connect ECONNREFUSED 127.0.0.1:8787
      at TCPConnectWrap.afterConnect [as oncomplete] (node:net:1645:16) {
    errno: -61,
    code: 'ECONNREFUSED',
    syscall: 'connect',
    address: '127.0.0.1',
    port: 8787
  }
}
```

### memory-governance

- Exit code: `1`
- Stdout tail:
```text
"error": "TypeError: fetch failed"
    },
    {
      "name": "Rejected learning proposal stays out of stored memory",
      "error": "TypeError: fetch failed"
    },
    {
      "name": "Memory curation API remains healthy after governance mutations",
      "error": "TypeError: fetch failed"
    }
  ],
  "warnings": [],
  "summary": {
    "passed": 0,
    "failed": 5,
    "warned": 0,
    "skipped": 0
  },
  "finished_at": "2026-05-15T15:57:14.416Z"
}
```

### approval-queue

- Exit code: `1`
- Stdout tail:
```text
"error": "TypeError: fetch failed"
    },
    {
      "name": "Approval history reflects both decisions",
      "error": "TypeError: fetch failed"
    },
    {
      "name": "Draft and vendor records remain reachable after queue updates",
      "error": "TypeError: fetch failed"
    }
  ],
  "warnings": [],
  "summary": {
    "passed": 0,
    "failed": 5,
    "warned": 0,
    "skipped": 0
  },
  "finished_at": "2026-05-15T15:57:14.533Z"
}
```

