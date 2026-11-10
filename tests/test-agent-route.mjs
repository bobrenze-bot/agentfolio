import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

// Load the Pages ES module without depending on functions/package.json's type.
const source = await readFile(new URL('../functions/api/v1/agents/[[path]].js', import.meta.url), 'utf8');
const { onRequest } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);

function context(path, url = 'https://example.invalid/api/v1/agents/ExampleAgent') {
  const reads = [];
  return {
    reads,
    request: new Request(url),
    params: path === undefined ? undefined : { path },
    env: {
      AGENTFOLIO_DATA: {
        async get(key) {
          reads.push(key);
          if (key === 'scores/exampleagent.json') {
            return JSON.stringify({ handle: 'ExampleAgent', name: 'Fixture Agent', composite_score: 42 });
          }
          if (key === 'profiles/exampleagent.json') {
            return JSON.stringify({ description: 'Offline fixture' });
          }
          return null;
        }
      }
    }
  };
}

for (const [name, path, url] of [
  ['Cloudflare catch-all array', ['ExampleAgent']],
  ['string parameter compatibility', 'ExampleAgent'],
  ['URL fallback without query contamination', undefined, 'https://example.invalid/api/v1/agents/ExampleAgent?view=full'],
  ['URL fallback with trailing slash', undefined, 'https://example.invalid/api/v1/agents/ExampleAgent/']
]) {
  test(name, async () => {
    const ctx = context(path, url);
    const response = await onRequest(ctx);
    assert.equal(response.status, 200);
    assert.deepEqual(ctx.reads, ['scores/exampleagent.json', 'profiles/exampleagent.json']);
    const body = await response.json();
    assert.equal(body.handle, 'ExampleAgent');
    assert.equal(body.composite_score, 42);
    assert.equal(body.profile.description, 'Offline fixture');
    assert.equal(response.headers.get('Access-Control-Allow-Origin'), '*');
    assert.equal(response.headers.get('Cache-Control'), 'public, max-age=300');
  });
}

for (const [name, path, url] of [
  ['empty array', []],
  ['empty string', ''],
  ['multiple array segments', ['ExampleAgent', 'extra']],
  ['multiple string segments', 'ExampleAgent/extra'],
  ['multiple URL segments', undefined, 'https://example.invalid/api/v1/agents/ExampleAgent/extra'],
  ['missing URL handle', undefined, 'https://example.invalid/api/v1/agents/']
]) {
  test(`rejects ${name} before storage access`, async () => {
    const ctx = context(path, url);
    const response = await onRequest(ctx);
    assert.equal(response.status, 400);
    assert.deepEqual(ctx.reads, []);
    assert.equal((await response.json()).usage, '/api/v1/agents/{handle}');
  });
}

test('unknown single-segment agent remains a 404 with a string handle', async () => {
  const ctx = context(['missing']);
  const response = await onRequest(ctx);
  assert.equal(response.status, 404);
  assert.deepEqual(await response.json(), { error: 'Agent not found', handle: 'missing' });
  assert.deepEqual(ctx.reads, ['scores/missing.json', 'profiles/missing.json']);
});
