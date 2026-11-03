import { afterEach, test, mock } from "node:test";
import assert from "node:assert/strict";
import { ApiError, API_URL, api, downloadReport, errorDetail, request, uploadFile } from "../lib/api.ts";
import { investigationHref, selectTransactions, validWebsite } from "../lib/workspace.ts";

afterEach(() => mock.restoreAll());

test("website validation allows only explicit web URLs without credentials", () => {
  for (const value of ["https://example.com", "http://example.org/path?q=1"]) assert.equal(validWebsite(value), true);
  for (const value of ["example.com", "javascript:alert(1)", "file:///etc/passwd", "https://user:password@example.com", "", "https://"]) assert.equal(validWebsite(value), false);
});

test("investigation links use resource IDs and preserve route type", () => {
  const resource_id = "resource/a";
  assert.equal(investigationHref({ investigation_type: "transaction_upload", resource_id }), "/transactions?upload=resource%2Fa");
  assert.equal(investigationHref({ investigation_type: "transaction", resource_id }), "/transactions/resource%2Fa");
  assert.equal(investigationHref({ investigation_type: "website_scan", resource_id }), "/website-scanner/resource%2Fa");
  assert.equal(investigationHref({ investigation_type: "unknown", resource_id }), null);
  assert.equal(investigationHref({ investigation_type: "website_scan", resource_id: null }), null);
});

test("transaction search, filters, and numeric sorting do not mutate source", () => {
  const rows = [
    { id: "1", transaction_reference: "Alpha", amount: 10, risk_level: "low", fraud_probability: 0.1, created_at: "2026-01-01" },
    { id: "2", transaction_reference: "Beta", amount: 100, risk_level: "high", fraud_probability: 0.9, created_at: "2026-01-02" },
    { id: "3", transaction_reference: "Alpha-2", amount: 50, risk_level: "high", fraud_probability: 0.8, created_at: "2026-01-03" },
  ];
  assert.deepEqual(selectTransactions(rows, "ALPHA", "high", "risk").map((row) => row.id), ["3"]);
  assert.deepEqual(selectTransactions(rows, "", "all", "amount").map((row) => row.id), ["2", "3", "1"]);
  assert.deepEqual(selectTransactions(rows, "", "all", "newest").map((row) => row.id), ["3", "2", "1"]);
  assert.deepEqual(rows.map((row) => row.id), ["1", "2", "3"]);
});

test("API reads direct response with no-store and expected base URL", async () => {
  const data = [{ id: "upload" }];
  const fetchMock = mock.method(globalThis, "fetch", async (url, init) => {
    assert.equal(url, `${API_URL}/api/transactions/history`);
    assert.equal(init.cache, "no-store");
    return Response.json(data);
  });
  assert.deepEqual(await api.uploads(), data);
  assert.equal(fetchMock.mock.callCount(), 1);
});

test("analysis uses exact JSON contract and encodes resource IDs", async () => {
  mock.method(globalThis, "fetch", async (url, init) => {
    if (init.method === "POST") {
      assert.equal(url, `${API_URL}/api/transactions/analyze`);
      assert.deepEqual(JSON.parse(init.body), { upload_id: "a/b" });
      assert.equal(init.headers["Content-Type"], "application/json");
    } else assert.equal(url, `${API_URL}/api/transactions/uploads/a%2Fb`);
    return Response.json({ id: "a/b" });
  });
  await api.analyze("a/b");
  await api.upload("a/b");
});

test("single prediction and phishing metrics use real backend routes", async () => {
  const calls = [];
  mock.method(globalThis, "fetch", async (url, init) => {
    calls.push(url);
    if (init.method === "POST") {
      assert.deepEqual(JSON.parse(init.body), { features: { Amount: 1 }, merchant_url: "https://example.com" });
    }
    return Response.json({});
  });
  await api.predict({ Amount: 1 }, "https://example.com");
  await api.websiteMetrics();
  assert.deepEqual(calls, [`${API_URL}/api/transactions/predict`, `${API_URL}/api/websites/metrics`]);
});

test("503 preserves backend detail and status; network failure is explicit", async () => {
  mock.method(globalThis, "fetch", async () => Response.json({ detail: "Fraud dataset unavailable" }, { status: 503 }));
  await assert.rejects(request("/test"), (error) => error instanceof ApiError && error.status === 503 && error.message === "Fraud dataset unavailable");
  mock.restoreAll();
  mock.method(globalThis, "fetch", async () => { throw new TypeError("fetch failed"); });
  await assert.rejects(request("/test"), /Cannot reach the ExplainPay API/);
  assert.equal(errorDetail({ detail: [{ msg: "invalid" }] }, "Fallback"), "Fallback");
});

test("report download rejects API failures rather than saving an error as PDF", async () => {
  mock.method(globalThis, "fetch", async () => Response.json({ detail: "Report does not exist" }, { status: 404 }));
  await assert.rejects(downloadReport("missing"), (error) => error instanceof ApiError && error.status === 404 && error.message === "Report does not exist");
});

test("report download retrieves a blob and clicks a download link", async () => {
  const previous = globalThis.document;
  const calls = [];
  mock.method(globalThis, "fetch", async (url, init) => {
    assert.equal(url, `${API_URL}/api/reports/report%2Fid/download`);
    assert.equal(init.cache, "no-store");
    return new Response("%PDF-1.4", { headers: { "Content-Type": "application/pdf" } });
  });
  mock.method(URL, "createObjectURL", (blob) => {
    assert.equal(blob.type, "application/pdf");
    return "blob:test-report";
  });
  mock.method(URL, "revokeObjectURL", (url) => calls.push(url));
  mock.method(globalThis, "setTimeout", (callback) => { callback(); return 1; });
  const anchor = { click() { calls.push("click"); }, remove() { calls.push("remove"); } };
  globalThis.document = {
    createElement(tag) { assert.equal(tag, "a"); return anchor; },
    body: { appendChild(element) { assert.equal(element, anchor); calls.push("append"); } },
  };
  try {
    await downloadReport("report/id");
    assert.equal(anchor.href, "blob:test-report");
    assert.equal(anchor.download, "explainpay-report-report/id.pdf");
    assert.deepEqual(calls, ["append", "click", "remove", "blob:test-report"]);
  } finally { globalThis.document = previous; }
});

test("XHR upload sends multipart file, reports progress, and returns direct response", async () => {
  const previous = globalThis.XMLHttpRequest;
  const progress = [];
  class FakeXHR {
    upload = {};
    status = 200;
    responseText = '{"id":"uploaded"}';
    open(method, url) {
      assert.equal(method, "POST");
      assert.equal(url, `${API_URL}/api/transactions/upload`);
    }
    send(form) {
      assert.equal(form.get("file").name, "transactions.csv");
      this.upload.onprogress({ lengthComputable: true, loaded: 5, total: 10 });
      this.onload();
    }
  }
  globalThis.XMLHttpRequest = FakeXHR;
  try {
    const result = await uploadFile(new File(["a,b\n1,2"], "transactions.csv"), (value) => progress.push(value));
    assert.equal(result.id, "uploaded");
    assert.deepEqual(progress, [50, 100]);
  } finally { globalThis.XMLHttpRequest = previous; }
});

test("XHR upload propagates service-unavailable errors", async () => {
  const previous = globalThis.XMLHttpRequest;
  class FailedXHR {
    upload = {};
    status = 503;
    responseText = '{"detail":"Database unavailable"}';
    open() {}
    send() { this.onload(); }
  }
  globalThis.XMLHttpRequest = FailedXHR;
  try {
    await assert.rejects(uploadFile(new File(["a"], "transactions.csv"), () => {}), (error) => error instanceof ApiError && error.status === 503 && error.message === "Database unavailable");
  } finally { globalThis.XMLHttpRequest = previous; }
});
