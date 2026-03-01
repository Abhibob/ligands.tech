# Calling GPT-OSS-120B on Modal

## Endpoint

```
https://benwu408--gpt-oss-120b-serve.modal.run
```

The server is OpenAI API-compatible, so you can use any OpenAI SDK or raw HTTP requests.

---

## Authentication

All requests require an API key passed via the `Authorization` header:

```
Authorization: Bearer YOUR_API_KEY
```

---

## Using curl

### Chat Completion

```bash
curl https://benwu408--gpt-oss-120b-serve.modal.run/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-oss-120b",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Explain quantum computing in simple terms."}
    ],
    "max_tokens": 4096
  }'
```

### List Models

```bash
curl https://benwu408--gpt-oss-120b-serve.modal.run/v1/models \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## Using Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://benwu408--gpt-oss-120b-serve.modal.run/v1",
    api_key="YOUR_API_KEY",
)

response = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain quantum computing in simple terms."},
    ],
    max_tokens=4096,
)

print(response.choices[0].message.content)
```

### Streaming

```python
stream = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[
        {"role": "user", "content": "Write a short poem about the ocean."},
    ],
    max_tokens=4096,
    stream=True,
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

---

## Using JavaScript/TypeScript

```typescript
import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "https://benwu408--gpt-oss-120b-serve.modal.run/v1",
  apiKey: "YOUR_API_KEY",
});

const response = await client.chat.completions.create({
  model: "openai/gpt-oss-120b",
  messages: [
    { role: "user", content: "Explain quantum computing in simple terms." },
  ],
  max_tokens: 4096,
});

console.log(response.choices[0].message.content);
```

---

## Reasoning Model Notes

GPT-OSS-120B is a **reasoning model**. Responses include a `reasoning_content` field showing the model's chain-of-thought, separate from the final `content` output.

```json
{
  "choices": [{
    "message": {
      "content": "The final answer.",
      "reasoning_content": "The model's internal reasoning steps..."
    }
  }]
}
```

To access reasoning in Python:

```python
message = response.choices[0].message
print("Reasoning:", message.reasoning_content)
print("Answer:", message.content)
```

---

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `model` | string | Must be `"openai/gpt-oss-120b"` |
| `messages` | array | Chat messages (`role` + `content`) |
| `max_tokens` | int | Max output tokens (including reasoning). Default varies. |
| `temperature` | float | Sampling temperature (0.0 - 2.0) |
| `top_p` | float | Nucleus sampling (0.0 - 1.0) |
| `stream` | bool | Stream response tokens |
| `stop` | string/array | Stop sequence(s) |

---

## Cold Start

The server has a 10-minute scaledown window. If no requests have been made recently, the first request will trigger a **cold start** (model loading takes several minutes). Subsequent requests will be fast.
