# FalconVerifier 工作总结（2026-09-25）

> ChaosButterfly · Hub71 Fish Tank 版。本文供团队内部阅读；对外材料见 `docs/talk.html`（英文 pitch）与 `docs/REPORT_falcon3b_arabic.pdf`（学术报告）。
> 代码与全部证据：<https://github.com/hw4375-collab/FalconVerifer>（PR #1）。

---

## 1. 我们做了什么（一句话）

**FalconVerifier 是一层可审计的中间件：Falcon 用阿拉伯语/英语作答，我们把它的每一步推理（CoT）和最终答案翻译成 Lean 4 命题，交给 Lean 内核证明或否证；被否证的步骤以自然语言反馈给 Falcon 让其修正；整个过程留下机器可验证的 assurance trace。**

产品主张（严格版，不夸大）：

- Lean 证明的是"被形式化的那条命题"，不是"Falcon 说的每个字"；
- 落在支持片段之外的句子明确标为 `unknown` / `skipped`，系统不装懂；
- "纠错"是"否证"的副产品——即使 Falcon 首轮就对，屏幕上每一步旁边的绿色 `verified` + 对应 Lean 命题也是有价值的证据（"CoT 可验证率"）。

## 2. 为什么是阿拉伯语 + Falcon（论证闭环）

1. Falcon 是 TII 的本土模型，大量用户用阿拉伯语；
2. 预训练数据中阿拉伯语占比小 → 阿拉伯语数学/逻辑推理更弱、更自信地出错（我们的数据：同一批题 3B 阿拉伯语基线 48–58%，7B 97%）；
3. 阿拉伯语文本还有放大错误的因素：东/西阿拉伯数字混用、RTL 与数字方向、丰富词形、VSO/SVO 自由语序、«إما…أو» 的排他/包含歧义；
4. 数学与逻辑的真值与语言无关——一旦译成 Lean 命题，判定权交给内核，绕开了"阿拉伯语数据稀缺"这个瓶颈；
5. 阿拉伯语语法高度规则（根-模板形态、固定量词句式 كل/بعض/لا أحد），适合 pregroup 代数语法做**确定性**（不调 LLM）解析；我们在 Lean 里证明了 VSO≡SVO 语义等价，语序归一化是安全的；
6. 因此验证 + 反馈把 3B 从 58% 提到 88%（86 题）、48% 提到 76%（245 题），0 回归。

**不要说的**："阿拉伯语比英语更适合形式化"。正确说法是"形式化对任何语言同样有效，而阿拉伯语在 Falcon 上收益最大（低基线 + 高歧义），且其规则语法让确定性片段可行"。

## 3. 系统架构（内部构建）

```
用户/评委 ──► Web UI (FastAPI + SSE) / CLI / POST /api/solve
                       │
                       ▼
              agent.py  验证-教学闭环（≤3 轮）
                       │
   ┌───────────────────┼─────────────────────┐
   ▼                   ▼                     ▼
student.py        formalizer.py         lean_runner.py
Falcon 学生模型   NL → Lean 4 命题       写 .lean 文件 → lake env lean
(3B/7B/H1R)       ① 确定性 pregroup 片段  → 解析内核输出
提取 CoT 步骤        arabic.py 算术        → verified / refuted /
                     arabic_logic.py 量词    unknown / ill_formed
                     arabic_graph.py 关系
                  ② Falcon-34B（或 GPT）兜底
                     + 结构化 round-trip 忠实性检查
                       │
                       ▼
                 feedback.py  把 refuted 步骤翻成阿拉伯语/英语教学反馈
                       │
                       ▼
            schemas.py  AssuranceTrace（每轮答案、命题、verdict、反馈、Lean 源码）
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   bench.py        dpo_export.py    server.py 静态页
   基准评测        偏好数据导出      /  /benchmark  /about
```

### 3.1 Python 包 `falconverifier/`（约 4.2k 行）

| 模块 | 职责 |
|---|---|
| `llm.py` | Falcon（Open WebUI 兼容 API）与 OpenAI/OpenRouter 客户端，统一接口 |
| `student.py` | 学生 Falcon 提示词（阿/英）、`FINAL ANSWER` 与步骤抽取 |
| `arabic.py` | 阿拉伯语算术片段：东西数字归一、百分比/折扣/运算顺序，pregroup 词典 + 解析器 → Lean 命题 |
| `arabic_logic.py` | 量词/条件/析取逻辑片段（三段论、逆否、非法换位、排他或），输出一阶命题 |
| `arabic_graph.py` | 对称二元关系与度数/奇偶片段（握手、朋友），输出 `Regular f k` 类命题 |
| `arabic_word.py` | 数量叙事应用题片段（装箱后再送出、复合折扣、购买付款、平均数、整除装箱、想一个数），按从句折叠成算术命题；未完全识别则返回 `None` 交给 LLM |
| `formalizer.py` | 片段路由 → 确定性翻译；片段外调用 LLM 形式化器，附 round-trip 忠实性检查（不一致降 `unknown`） |
| `lean_runner.py` | 生成 Lean 文件（每步一个 `example`，正反各试），按片段选战术（`norm_num`/`decide`/`omega`/握手引理），解析错误映射回步骤 |
| `verifier.py` | 组装 `VerificationReport`，判定最终答案是否与命题一致 |
| `feedback.py` | 教学反馈模板（阿/英），只包含自然语言 + Lean 验证过的等式 |
| `agent.py` | 闭环编排、SSE 事件、`assurance_score` |
| `bench.py` / `bench/report.py` | 基准运行、切片统计、BENCHMARK.md 生成 |
| `dpo_export.py` | trace → DPO 偏好对（见 §6） |
| `server.py` | FastAPI：`/api/solve`、`/api/solve/stream`、`/api/check`、`/api/bench/*`、`/healthz`、三页静态 UI |
| `cli.py` | `falconverifier solve/serve/bench/export-dpo` |

### 3.2 Lean 项目 `lean/`（Lean 4 + Mathlib）

- `FalconVerifier/Prelude.lean`：通用引理、ℚ 提升、`nlinarith` 守卫；
- `FalconVerifier/Graph.lean`：`IsGraph`、`degree`、`Regular`，握手引理 `∑ degree = 2|E|`，度数上界；40 组 (n,k) 的存在/不存在定理（circulant 见证），五人题 `∀ f : Fin 5 → Fin 5 → Bool, ¬ Regular f 3` 18 秒证毕，无暴力枚举；
- `FalconVerifier/Arabic/Pregroup.lean`、`Semantics.lean`、`ArabicTypes.lean`：阿拉伯语 pregroup 类型、约化到句子类型的证书、VSO≡SVO 语义等价定理、"一致性特征丢失 → 不可导出"定理（说明粗粒度语法会丢忠实性，是研究方向）。

### 3.3 verdict 与 assurance 语义

| verdict | 含义 |
|---|---|
| `verified` | Lean 证明了 P |
| `refuted` | Lean 证明了 ¬P |
| `unknown` | 两边都没证出（超时/战术不足/忠实性检查失败） |
| `ill_formed` | 命题无法类型检查 |
| `skipped` | 不是可检查命题（"我们来计算…"这类叙述句） |

`assurance_score = ½ ×（最后一轮可检查步骤中 verified 的比例）+ ½ ×（最终答案 verdict 分值：verified 1 / unknown 0.4 / refuted 0）`。它不是模型置信度，也不宣称覆盖全部自然语言语义。

## 4. Benchmark 证据（全部从 `bench/results/*/results.json` 自动生成）

### 4.1 主结果：Falcon 自形式化（学生 3B/7B，形式化器 Falcon-H1-Arabic-34B）

| run | n | 基线 | 验证后 | 基线错误 | Lean 检出 | 修正 | 误报 | 回归 | 轮数 | 时延 |
|---|---|---|---|---|---|---|---|---|---|---|
| 3B 阿拉伯语 86 题 | 86 | 58.1% | **88.4%** | 36 | 33 (91.7%) | 26 | 1 | 0 | 1.69 | 39.4 s |
| 3B 阿拉伯语 245 题（扩展） | 244 | 47.9% | **76.2%** | 127 | 117 (92.1%) | 69 | 1 | 0 | 1.86 | 40.8 s |
| 7B 阿拉伯语 76 题 | 76 | 97.4% | 98.7% | 2 | 1 | 1 | 1 | 0 | 1.04 | 22.9 s |
| 3B 英文 89 题 | 89 | 61.8% | 78.6% | 34 | 26 | — | — | 0 | — | — |
| 7B 英文 89 题 | 89 | 96.6% | 98.9% | 3 | 2 | — | — | 0 | — | — |

切片亮点（86 题 run）：东阿拉伯数字题 54.8% → 83.9%；确定性片段内题 68.8% → 93.8%，检出率 100%，0 误报。

### 4.2 CoT 可验证率（新叙事："Lean 逐步审核 Falcon 的思维链"）

| run | 轮数 | 步骤数 | 步骤被判定 | verified | refuted | unknown | skipped | 最终答案被判定 |
|---|---|---|---|---|---|---|---|---|
| 86 题 | 145 | 395 | 53.2% | 49.9% | 3.3% | 4.6% | 42.3% | 95.9% |
| 245 题 | 453 | 1314 | 54.6% | 50.7% | 3.9% | 3.4% | 41.9% | 97.6% |

讲法："每一轮 Falcon 输出，Lean 对超过一半的 CoT 句子和 96–98% 的最终答案给出机器证明级判定；其余明确标为不判定而非猜测。"

### 4.3 诚实修正

生成器曾有 6 题标准答案取整错误（如 150×85%=127.5 被标 128），3B 实际答对却被判错；已排除并修好生成器，DPO 导出因"须匹配标准答案"未受污染。

## 5. Web UI（评委 5 分钟流程）

三页，ChaosButterfly 白底海军蓝、衬线标题：

- **`/` 验证器**（本轮重点优化）
  1. 顶部 5 步说明 + verdict 图例；
  2. 示例按钮带 **3B 首轮错误率徽章**（从 `/api/bench/hardness` 实时统计所有 3B run，如 `3B ✗ 4/4`），点阿拉伯语示例自动填英文翻译、标准答案，并自动切到 3B 弱学生；
  3. 运行中显示已用秒数与 **Stop** 按钮；
  4. 每轮卡片：Falcon 原文（RTL）→ 逐步 Lean 命题 → verdict 徽章；新增 **CoT 可验证率条**（verified/refuted/unknown/skipped 分段）；refuted 行高亮；"Lean 4 source sent to the kernel (audit)" 折叠面板展示真实送入内核的文件；
  5. 教学反馈原文（RTL）；
  6. 结果 KPI：状态 + 一句话故事（"round 1 refuted → taught → round 2 verified"）、最终答案、assurance、**全程被 Lean 判定的命题数**、轮数/时间、download trace（完整 JSON）；
  7. **"No time to wait? Replay a recorded correction"**：从已提交 benchmark trace 里挑 6 道 3B 首轮错→Lean 抓到→修正的题（3 数学 + 3 逻辑），一键回放，零模型调用——现场不必赌 3B 会犯错。
- **`/benchmark`**：基线 vs 验证后柱状图、8 个 run 的切片表、逐题展开（金标/基线/最终/Lean 判定），每题、results.json、trace、题库、判分代码都链接到 GitHub；"view" 在验证器里回放。
- **`/about`**：闭环、verdict 语义、为什么阿拉伯语、pregroup、五人题示例、局限。

## 6. 方向 3：Lean 反馈数据飞轮（DPO 导出）

`falconverifier export-dpo` 把 trace 转成偏好对：`prompt` / `rejected`（被 Lean 否证的早轮回答）/ `chosen`（后轮、Lean 验证且与金标一致）/ `evidence`（否证命题、内核诊断、反馈）。规则：unknown 不算 rejected；不使用任何 LLM 裁判；去重 `(prompt, rejected)`；保留语言与轮次元数据。

当前 `data/dpo_pairs.jsonl`：**294 对（226 阿 / 68 英）**，来自 1038 条 trace，33 重复被丢弃。下一步（需 ≥24 GB GPU）：对开源 Falcon-H1-3B 做 LoRA-DPO，用同一 benchmark 只测第 1 轮准确率——若上升即证明"形式化反馈可内化进模型"。caveat：chosen 文本带修订口吻（«التصحيح:»），训练前需清洗。

## 7. 基础设施与部署

- **测试**：99 个 pytest（含 Lean 集成、页面、证据 API、路径穿越、trace 回放、hardness）+ `lake build`；CI（ruff + pytest）绿。
- **Docker**：`Dockerfile` 内含 elan + Mathlib 缓存；`.github/workflows/docker.yml` 在 main 合并后自动发布 `ghcr.io/hw4375-collab/falconverifer:latest`。
- **部署**：`deploy/docker-compose.yml`（Caddy 自动 HTTPS、限流、访问令牌、健康检查）、`deploy/install.sh`（`FV_IMAGE=... bash deploy/install.sh` 直接拉镜像，免现场编译 20 分钟）、`docs/DEPLOY.md`。**唯一卡点：等服务器/域名凭证。**
- **性能**：`/api/bench/runs`、`/api/bench/hardness` 按 results.json mtime 缓存（20 ms → 6 ms）；Lean 每轮 4–40 s，Falcon 调用 5–20 s；preview 隧道会额外拖慢交互，本地/服务器部署无此问题。
- **中间件形态**：`curl POST /api/solve` 一行接入，返回 verdict + assurance + 完整 trace，任何调用 Falcon 的应用都可加验证层。

## 8. 交付物清单

| 文件 | 内容 |
|---|---|
| `docs/talk.html` / `docs/talk.pdf` | 英文 pitch（阿拉伯语原文 + 英文翻译） |
| `docs/REPORT_falcon3b_arabic.pdf` | 学术报告（固定在原 76 题 run） |
| `docs/BENCHMARK.md` | 全部 run 的自动生成表格与逐题清单 |
| `docs/ARABIC.md` | 为什么阿拉伯语、pregroup、形态学忠实性 |
| `docs/DPO.md` | 数据飞轮规则与 caveats |
| `docs/DEPLOY.md` / `docs/DEMO.md` | 上线与演示脚本 |
| `data/dpo_pairs.jsonl` | 294 条带 Lean 证据的偏好对 |
| `bench/results/**` | 8 个 run 的 results.json + 每题 trace |
| Web UI（`/`, `/benchmark`, `/about`） | preview 在线；服务器凭证到位后 30–45 分钟上线 |

## 9. 局限与下一步

**局限**
- 只覆盖可判定片段（算术、百分比、量词逻辑、对称关系/计数）；证明题、代数应用题为 `unknown`。
- LLM 形式化器（34B）在二元关系上会丢结构；确定性片段 + round-trip 检查把它降为 `unknown` 而非误报，但逐步忠实性仍是弱环。
- 3B 采样导致现场可能首轮就对——用"CoT 可验证率"叙事 + 回放兜底。
- 每题 30–40 s 时延；DPO 内化后可去掉推理时的 Lean 成本（待验证）。

**下一步**
1. 服务器上线 + 二维码；
2. LoRA-DPO 弱版本证明概念（GPU）；
3. Open WebUI Pipe（"Falcon + Lean Verified"模型选项）；
4. 扩片段：比例/比率、简单代数方程、日期/时间。
