"use strict";
const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");

const html = fs.readFileSync("web/index.html", "utf8");
const script = html.split("<script>")[1].split("</script>")[0];
const core = script.split("function show(report)")[0];
const inspect = vm.runInNewContext(core + "\ninspect", {});

const patient = inspect({resourceType:"Patient",id:"p1"});
assert.equal(patient.valid, true);
assert.equal(patient.issue_count, 0);
assert.equal(patient.operationOutcome.issue[0].severity, "information");

const missing = inspect({resourceType:"Observation",id:"o1"});
assert.equal(missing.valid, false);
assert.equal(missing.issue_count, 2);

const bundle = JSON.parse(fs.readFileSync("sample_fhir_bundle.json","utf8"));
const resolved = inspect(bundle);
assert.equal(resolved.valid,true);
assert.equal(resolved.resources_checked,3);
assert.equal(resolved.issue_count,0);

bundle.entry[1].resource.subject.reference = "urn:uuid:missing";
assert.equal(inspect(bundle).valid,false);

const illegal = inspect({resourceType:"Bundle",type:"collection",total:10,entry:[{}]});
assert.equal(illegal.valid,false);

const sensitive = inspect({resourceType:"Patient",id:"Patient Jane Smith"});
assert.equal(sensitive.valid,false);
assert.equal(JSON.stringify(sensitive).includes("Jane Smith"),false);

console.log("Browser validator logic smoke checks passed.");
