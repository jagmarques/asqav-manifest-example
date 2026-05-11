# Asqav + Manifest example

Two questions you have to answer for any AI agent in regulated work:

1. Which model did this query go to, and what did it cost?
2. What action did the agent take, and is the receipt verifiable?

[Manifest](https://github.com/mnfst/manifest) answers question 1. It is a smart model router with a `/v1/chat/completions` proxy that picks a provider based on cost, capability, or your custom headers. [Asqav](https://github.com/jagmarques/asqav) answers question 2. It signs every agent action with a NIST PQC signature (ML-DSA-65), anchors the receipt in Bitcoin via OpenTimestamps, and gives you a public verify URL.

Stack them and you get the full record of what your agent did, with a defensible trail of which LLM produced which output.

## What this repo is

A 60-line Python script (`agent.py`) that:

1. Sends the prompt to Manifest at `http://localhost:2099/v1/chat/completions`. Manifest picks the model.
2. Wraps the resulting tool call in `asqav.action()`. Asqav signs it.
3. Prints the verify URL plus the model and cost Manifest reported.

That is the whole pattern. You keep your existing OpenAI-compatible code and add two bracket lines around the action you want signed.

## Run it

You need Manifest running locally and an Asqav API key.

```bash
# Manifest, self-hosted
bash <(curl -sSL https://raw.githubusercontent.com/mnfst/manifest/main/docker/install.sh)
# Open http://localhost:2099 and add at least one provider API key

# Asqav cloud key
# Sign up at https://www.asqav.com and copy the sk_live_... key

pip install asqav openai
export ASQAV_API_KEY=sk_live_xxx
python agent.py "Wire 1500 EUR to vendor INV-2026-04-12"
```

The script prints something like:

```
Manifest routed to: claude-haiku-4-5  cost: $0.0002
Asqav signature:    sig_a1b2c3d4e5f6
Verify:             https://www.asqav.com/verify/sig_a1b2c3d4e5f6
```

Click the verify URL. Anyone, including a regulator, can confirm the action was signed by your agent at that timestamp without a login.

## What is in agent.py

```python
import os, sys
from openai import OpenAI
import asqav

# Manifest is OpenAI-compatible; point the SDK at its proxy.
manifest = OpenAI(
    base_url="http://localhost:2099/v1",
    api_key=os.environ.get("MANIFEST_API_KEY", "dev-api-key-12345"),
)

# Asqav governs the agent itself.
asqav.init(api_key=os.environ["ASQAV_API_KEY"])
agent = asqav.Agent.create("finance-bot", capabilities=["wire_transfer"])

prompt = sys.argv[1] if len(sys.argv) > 1 else "noop"

# Step 1: Manifest picks the model and runs the call.
resp = manifest.chat.completions.create(
    model="auto",
    messages=[
        {"role": "system", "content": "Extract structured wire-transfer details from the user request."},
        {"role": "user", "content": prompt},
    ],
)
model = resp.model
text = resp.choices[0].message.content
cost = float(resp.usage.total_tokens) * 0.000002  # placeholder

# Step 2: Asqav signs the agent action so it has a verifiable Compliance Receipt.
sig = agent.sign(
    "wire_transfer",
    context={"prompt": prompt, "extracted": text, "model": model, "cost_usd": cost},
    receipt_type="protectmcp:decision",
    risk_class="high",
    model_name=model,
)

print(f"Manifest routed to: {model}  cost: ${cost:.4f}")
print(f"Asqav signature:    {sig.signature_id}")
print(f"Verify:             {sig.verification_url}")
```

## Why pair them

Manifest's data model is "request to a model": which model, how many tokens, how much. Asqav's data model is "action by an agent": who did what, signed with what key, anchored where. Different shapes, no overlap. You want both.

A few patterns that come up:

- Routing decisions become evidence. The model Manifest picked is metadata on the Asqav signature, so a year from now you can answer "what model was used for this signature" without joining anything.
- Cost attribution becomes per-action. Manifest tracks dollars per request; Asqav tracks signatures per action. Multiply once, attach to the receipt.
- A regulator only needs the verify URL. Public, no login, ML-DSA-65 + OTS, and it now also returns a per-axis verification detail (signer key match, signature valid, algorithm match, agent active) so a court can read the failure mode without your code.

## License

MIT.
