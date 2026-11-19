# Isolating Perception for Multi-View Planning under Occlusion-Induced Partial Observability

Code and data for [Isolating Perception for Multi-View Planning under Occlusion-Induced Partial Observability](https://arxiv.org/abs/2611.19179).

A vision-language model (VLM) sees each blocksworld state from two camera views, neither of
which shows the whole scene, and must produce a plan from the initial to the goal state. We
compare three ways of using the VLM:

- **VLM-as-planner** (`planner`): the VLM outputs the plan directly.
- **VLM-as-formalizer** (`formalizer`): the VLM outputs the PDDL facts of each state, and a
  classical planner (Fast Downward) solves the resulting problem.
- **VLM-as-perceiver** (`perceiver`): the VLM only describes the stacks it sees in each
  view. A constraint solver reconciles the views into one physically consistent state,
  which Fast Downward then solves.

## Setup

Tested with Python 3.12. Install the dependencies:

```bash
pip install -r requirements.txt
pip install vllm==0.23.0  # only to serve open-weight models locally
```

Install the [Fast Downward](https://github.com/aibasel/downward) planner into `downward/`.
Any recent release works; see its
[build instructions](https://github.com/aibasel/downward/blob/main/BUILD.md) for
prerequisites:

```bash
git clone https://github.com/aibasel/downward.git downward
cd downward && ./build.py && cd ..
```

To use another location, pass `--fast_downward_dir` to `src/main.py`.

API credentials are read from the environment or from a `.env` file in the repository root:

| Variable | Used for |
|---|---|
| `GEMINI_API_KEY` or `GOOGLE_API_KEY` | Gemini through the Gen AI API (with `--no-batch`) |
| `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `VERTEX_BATCH_BUCKET` | Gemini through Vertex AI; batch mode, the default, needs a project and bucket |
| `OPENROUTER_API_KEY` | Models served through OpenRouter (`--use_openrouter`) |
| `VLLM_PORT` or `VLLM_BASE_URL` | A vLLM server for open-weight models |

## Data

`data/` holds the six BW-PO datasets, each with 110 problems:

| Paper | Directory |
|---|---|
| BW-PO-DEPTH | `data/blocksworld_depth` |
| BW-PO-6 | `data/blocksworld_po` |
| BW-PO-12 | `data/blocksworld_po_12` |
| BW-PO-20 | `data/blocksworld_po_20` |
| BW-PO-40 | `data/blocksworld_po_40` |
| BW-PO-100 | `data/blocksworld_po_100` |

Each dataset has a `domain.pddl`, and each `problem_<N>/` holds the ground-truth
`problem.pddl`, an optimal `plan.txt`, and two views of each state in
`observations/{init,goal}_{1,2}.jpg`.

## Running experiments

Run everything from the repository root. A single experiment:

```bash
python src/main.py --model_name Gemini-3.1-Pro --use_gemini --no-batch --dataset blocksworld_depth --mode perceiver
```

`--mode` is one of `planner`, `formalizer`, `perceiver`, or the prompt-level baselines
`planner_priors` and `formalizer_priors`, which add the scene's physical constraints to the
prompt. Model names are defined in `src/models/config.py`. See `python src/main.py --help`
for all options.

**Open-weight models (vLLM).** Start a server, then run experiments against its port:

```bash
scripts/serve_vllm.sh --model Gemma-4-31B --gpus 0,1
scripts/run_vllm.sh --model Gemma-4-31B --port 8000
```

`run_vllm.sh` runs every dataset and mode by default with thinking enabled. Use
`--datasets`, `--modes`, `--no-thinking` and `--repeats` to change this, and `--dry-run` to
print the commands without running them.

**Gemini.** `scripts/run_gemini.sh` takes the same flags and runs through the Gemini API.

Both scripts activate the virtual environment at `$VENV` if it is set.

Each run writes to `results/<dataset>/<mode>/<model>/<timestamp>/`. The directory holds
`eval_report.json`, with plan success rate, state precision and recall, and token usage,
and one directory per problem with the prompts, responses and plans.

## Citation

```bibtex
@inproceedings{nguyen2027isolatingperception,
      title={Isolating Perception for Multi-View Planning under Occlusion-Induced Partial Observability},
      author={Kevin Nguyen and Ceyhun Efe Kayan and Feng Liu and Li Zhang},
      booktitle={Proceedings of the 20th Conference of the European Chapter of the Association for Computational Linguistics},
      year={2027},
      address={Athens, Greece},
      publisher={Association for Computational Linguistics},
}
```

## License

This code and data are released under the [MIT License](LICENSE).
