"""Minimal example: Manifest routes the LLM, Asqav signs the agent action.

Two SDKs, one flow:

  prompt
    -> Manifest /v1/chat/completions (picks the model)
    -> agent decides on an action
    -> Asqav signs the action with ML-DSA-65 (verifiable receipt)
    -> public verify URL anyone can audit

Run:
  pip install asqav openai
  export ASQAV_API_KEY=sk_live_...
  python agent.py "Wire 1500 EUR to vendor INV-2026-04-12"
"""
from __future__ import annotations

import os
import sys

import asqav
from openai import OpenAI


def main() -> int:
    prompt = sys.argv[1] if len(sys.argv) > 1 else "noop"

    manifest = OpenAI(
        base_url=os.environ.get("MANIFEST_BASE_URL", "http://localhost:2099/v1"),
        api_key=os.environ.get("MANIFEST_API_KEY", "dev-api-key-12345"),
    )

    asqav.init(api_key=os.environ["ASQAV_API_KEY"])
    agent = asqav.Agent(name="finance-bot", capabilities=["wire_transfer"])

    resp = manifest.chat.completions.create(
        model="auto",
        messages=[
            {
                "role": "system",
                "content": "Extract structured wire-transfer details from the user request.",
            },
            {"role": "user", "content": prompt},
        ],
    )
    model = resp.model
    text = resp.choices[0].message.content or ""
    tokens = resp.usage.total_tokens if resp.usage else 0
    cost = float(tokens) * 0.000002  # placeholder unit price

    with agent.action(
        action_type="wire_transfer",
        payload={"prompt": prompt, "extracted": text},
    ) as a:
        a.metadata["model"] = model
        a.metadata["cost_usd"] = cost
        sig_id = a.signature_id

    print(f"Manifest routed to: {model}  cost: ${cost:.4f}")
    print(f"Asqav signature:    {sig_id}")
    print(f"Verify:             https://www.asqav.com/verify/{sig_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
