# Display Templates

This file defines the English-first templates for web cards and email digests.

## 1. Web Card Template

### Single Story Template (with image)

```markdown
### {display_title}

> **Tags:** `tag1` `tag2`
>
> **Source:** [Read more]({source_url}) · {publish_date}

{English summary paragraph explaining what happened and why it matters}

- {key point 1}
- {key point 2}
- {key point 3}

For `Breakout AI Products`, the summary and bullets should emphasize the product's distinctive capabilities, advantages, and launch novelty instead of stopping at a generic functional description.

![{image_alt}]({image_url})

---
```

### Single Story Template (without image)

```markdown
### {display_title}

> **Tags:** `tag1` `tag2`
>
> **Source:** [Read more]({source_url}) · {publish_date}

{English summary paragraph}

- {key point 1}
- {key point 2}
- {key point 3}

---
```

## 2. Section Page Template

```markdown
# {section_name} — {YYYY-MM-DD}

> {N} stories in today's digest

## {tag_group}

### {display_title_a}

> **Tags:** `tag1` `tag2`
>
> **Source:** [Read more](https://example.com) · 2025-03-06

English summary paragraph...

- Key point one
- Key point two
- Key point three

For breakout-product cards, make the bullets concretely explain feature depth, strengths, and what makes the product newly worth watching.

---

### {display_title_b}

> **Tags:** `tag1`
>
> **Source:** [Read more](https://example.com) · 2025-03-06

English summary paragraph...

- Key point one
- Key point two
- Key point three

![Preview image](https://example.com/image.png)

---
```

## 3. Email Digest Template

```markdown
# {section_name} · Daily AI Brief

> {YYYY-MM-DD} · {N} stories

---

## Top Stories

1. **{display_title_1}** — {one-sentence English takeaway}
2. **{display_title_2}** — {one-sentence English takeaway}
3. **{display_title_3}** — {one-sentence English takeaway}

---

## Full Brief

### {tag_group}

#### {display_title_1}

> `tag1` · [Read more]({source_url})

{English summary paragraph}

- {key point 1}
- {key point 2}
- {key point 3}

---

#### {display_title_2}

> `tag1` `tag2` · [Read more]({source_url})

{English summary paragraph}

- {key point 1}
- {key point 2}
- {key point 3}

---

## More

- [Open the full web version]({web_link})
- [Manage subscription settings]({settings_link})

---

> This email was generated automatically · [Unsubscribe]({unsubscribe_link})
```

## 4. Filled Example

### Web Card Example

```markdown
### Meta expands the Llama 4 line with Scout and Maverick

> **Tags:** `Language Models` `Architecture`
>
> **Source:** [Read more](https://ai.meta.com/blog/llama-4) · 2025-03-05

Meta introduced two new models in the Llama 4 family, positioning Scout for lighter deployment and Maverick for larger-scale reasoning workloads. The release matters because it expands Meta's open model lineup and gives developers more deployment choices.

- Scout is framed as the lighter-weight model in the release.
- Maverick is positioned as the larger MoE option.
- Both models were announced as part of the same launch.

![Llama 4 architecture](https://example.com/llama4.png)

---
```

### Email Top Stories Example

```markdown
## Top Stories

1. **Meta broadens Llama 4 with two deployment profiles** — The launch adds both lighter and larger model options.
2. **Runway pushes its video stack further upmarket** — The update signals another move toward longer, higher-fidelity generation.
3. **OpenAI's latest financing sharpens the competitive backdrop** — The funding round raises the stakes across the AI platform market.
```
