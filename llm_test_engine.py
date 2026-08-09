#!/usr/bin/env python3
"""
llm_test_engine.py - General-purpose LLM-based MDTE testing engine.

Given ANY single-class Java source file (via CLI arg), this engine:
  1. Prompts an LLM to perform Input Space Partitioning (ISP) and Base Choice
     Coverage (BCC) as an explicit, visible intermediate artifact.
  2. Has the LLM generate a compilable JUnit 4 test class from that artifact.
  3. Compiles the result with javac. On failure, feeds the compiler error back
     to the LLM once (Generation-Validation-Repair, budget = 1) and retries.
  4. Runs the compiled test with org.junit.runner.JUnitCore and captures the
     real pass/fail result.
  5. Writes a full transcript log and renders it as a PNG "terminal
     screenshot" (this sandbox is headless / has no IDE, so a rendered
     terminal transcript is used as the visual evidence artifact instead).

Usage:
    python llm_test_engine.py <path/to/ClassName.java> [--backend claude|openai]

Backends:
    claude  - shells out to the local `claude -p` CLI (no API key needed;
              uses this environment's already-authenticated Claude Code
              session). This is what the demo run in this submission uses.
    openai  - real OpenAI Chat Completions API call (needs OPENAI_API_KEY).
              Included so the engine is provider-agnostic ("general purpose"
              across LLM vendors, not just across target files).
"""
import argparse
import os
import re
import subprocess
import sys
from abc import ABC, abstractmethod
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIB_DIR = HERE / "lib"
OUT_DIR = HERE / "out"
CLASSPATH_SEP = ";" if os.name == "nt" else ":"


# --------------------------------------------------------------------------- #
# 1. LLM backends (pluggable)
# --------------------------------------------------------------------------- #
class LLMBackend(ABC):
    @abstractmethod
    def complete(self, prompt: str) -> str:
        ...


class ClaudeCLIBackend(LLMBackend):
    """Calls the local `claude` CLI in non-interactive print mode."""

    def complete(self, prompt: str) -> str:
        result = subprocess.run(
            ["claude", "-p", prompt, "--allowedTools", ""],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode != 0:
            raise RuntimeError(f"claude CLI failed (rc={result.returncode}): {result.stderr[:500]}")
        return result.stdout.strip()


class OpenAIBackend(LLMBackend):
    """Real OpenAI API backend. Requires `pip install openai` and OPENAI_API_KEY."""

    def __init__(self, model: str = "gpt-4o"):
        from openai import OpenAI  # imported lazily so this file works w/o the package
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = model

    def complete(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()


def get_backend(name: str) -> LLMBackend:
    if name == "claude":
        return ClaudeCLIBackend()
    if name == "openai":
        return OpenAIBackend()
    raise ValueError(f"Unknown backend: {name}")


# --------------------------------------------------------------------------- #
# 2. Prompt construction (MDTD-structured, two-part delimited output)
# --------------------------------------------------------------------------- #
PROMPT_TEMPLATE = """You are a Software Quality Engineer applying Model-Driven Test Design (MDTD).

Analyze the Java class below and produce your answer in EXACTLY this format,
with no markdown code fences and no extra commentary outside the markers:

===ISP===
(Plain text. List the Input Space Partitioning characteristics for each
parameter of the public method(s), then list the Base Choice Coverage (BCC)
test requirements: one base test choosing the most "normal" block for every
characteristic, then one test per characteristic that varies ONLY that
characteristic to an edge/invalid block while holding the others at base.)
===JAVA===
(A complete, compilable JUnit 4 test class named {class_name}Test, package-less,
importing only org.junit.Test and org.junit.Assert.*, that implements every
BCC requirement listed above as one @Test method each. Use assertEquals /
assertThrows-style try-catch for exceptions. The class under test is called
{class_name} and is on the compile classpath already -- do not redefine it.)
===END===

Java source (file: {file_name}):
```java
{java_source}
```
"""

REPAIR_TEMPLATE = """Your previous JUnit 4 test class failed to compile.

Compiler error:
{compile_error}

Previous code:
{previous_code}

Fix the class and respond again in EXACTLY the same ===ISP===/===JAVA===/===END===
format as before (ISP section may just say "unchanged"). No markdown fences.
"""


def build_prompt(java_file: Path) -> str:
    class_name = java_file.stem
    java_source = java_file.read_text()
    return PROMPT_TEMPLATE.format(class_name=class_name, file_name=java_file.name, java_source=java_source)


# --------------------------------------------------------------------------- #
# 3. Response parsing
# --------------------------------------------------------------------------- #
def parse_response(text: str):
    isp_match = re.search(r"===ISP===(.*?)===JAVA===", text, re.DOTALL)
    java_match = re.search(r"===JAVA===(.*?)(===END===|$)", text, re.DOTALL)
    isp = isp_match.group(1).strip() if isp_match else "(ISP section not found in response)"
    java_code = java_match.group(1).strip() if java_match else text.strip()
    # strip stray markdown fences if the model added them anyway
    java_code = re.sub(r"^```(java)?\s*", "", java_code)
    java_code = re.sub(r"```\s*$", "", java_code).strip()
    return isp, java_code


# --------------------------------------------------------------------------- #
# 4. Compile + run verification loop
# --------------------------------------------------------------------------- #
def compile_test(class_name: str, target_java: Path, out_dir: Path):
    cp = CLASSPATH_SEP.join([str(LIB_DIR / "junit-4.13.2.jar"), str(LIB_DIR / "hamcrest-core-1.3.jar")])
    cmd = [
        "javac", "-cp", cp, "-d", str(out_dir),
        str(target_java), str(out_dir / f"{class_name}Test.java"),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, (result.stdout + result.stderr)


def run_test(class_name: str, out_dir: Path):
    cp = CLASSPATH_SEP.join([
        str(LIB_DIR / "junit-4.13.2.jar"),
        str(LIB_DIR / "hamcrest-core-1.3.jar"),
        str(out_dir),
    ])
    cmd = ["java", "-cp", cp, "org.junit.runner.JUnitCore", f"{class_name}Test"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, (result.stdout + result.stderr)


# --------------------------------------------------------------------------- #
# 5. Evidence rendering (PNG "terminal transcript" screenshot substitute)
# --------------------------------------------------------------------------- #
_ASCII_MAP = str.maketrans({
    "—": "-", "–": "-", "‘": "'", "’": "'",
    "“": '"', "”": '"', "…": "...", "→": "->",
})


def render_evidence_png(transcript: str, out_path: Path, title: str):
    from PIL import Image, ImageDraw, ImageFont

    transcript = transcript.translate(_ASCII_MAP)
    title = title.translate(_ASCII_MAP)
    font = None
    for candidate in (r"C:\Windows\Fonts\consola.ttf", r"C:\Windows\Fonts\cour.ttf"):
        if Path(candidate).exists():
            font = ImageFont.truetype(candidate, 15)
            break
    if font is None:
        font = ImageFont.load_default()

    lines = []
    for raw_line in transcript.splitlines():
        while len(raw_line) > 110:
            lines.append(raw_line[:110])
            raw_line = raw_line[110:]
        lines.append(raw_line)

    line_h = 19
    width = 1000
    height = 40 + line_h * len(lines) + 20
    img = Image.new("RGB", (width, height), (18, 18, 18))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, width, 34], fill=(40, 40, 40))
    draw.text((12, 8), title, fill=(0, 255, 120), font=font)
    y = 42
    for line in lines:
        color = (0, 255, 120) if line.startswith("$") else (220, 220, 220)
        if "FAILURES" in line or "Error" in line or "error:" in line:
            color = (255, 90, 90)
        if "OK (" in line or "Success" in line:
            color = (120, 255, 120)
        draw.text((12, y), line, fill=color, font=font)
        y += line_h
    img.save(out_path)


# --------------------------------------------------------------------------- #
# 6. Orchestration
# --------------------------------------------------------------------------- #
def process(java_file: Path, backend_name: str, repair_budget: int = 1):
    class_name = java_file.stem
    backend = get_backend(backend_name)
    transcript = [f"$ python llm_test_engine.py {java_file.name} --backend {backend_name}", ""]

    print(f"[1/4] Prompting {backend_name} backend for MDTD analysis of {java_file.name} ...")
    prompt = build_prompt(java_file)
    response = backend.complete(prompt)
    isp, java_code = parse_response(response)
    transcript.append("=== ISP / Base Choice Coverage requirements (from LLM) ===")
    transcript.append(isp)
    transcript.append("")

    attempt = 0
    ok = False
    compile_out = ""
    while True:
        (OUT_DIR / f"{class_name}Test.java").write_text(java_code)
        print(f"[2/4] Compiling {class_name}Test.java (attempt {attempt + 1}) ...")
        ok, compile_out = compile_test(class_name, java_file, OUT_DIR)
        transcript.append(f"$ javac ... {class_name}Test.java   (attempt {attempt + 1})")
        transcript.append(compile_out.strip() or "(compiled with no warnings)")
        transcript.append("")
        if ok or attempt >= repair_budget:
            break
        print("      compile FAILED -- requesting repair from LLM ...")
        repair_prompt = REPAIR_TEMPLATE.format(compile_error=compile_out[:2000], previous_code=java_code)
        response = backend.complete(repair_prompt)
        isp2, java_code = parse_response(response)
        attempt += 1

    if not ok:
        print("[3/4] Compile failed after repair budget exhausted. See run log.")
        run_ok, run_out = False, "(skipped: compile did not succeed)"
    else:
        print("[3/4] Compile OK. Running JUnit ...")
        run_ok, run_out = run_test(class_name, OUT_DIR)
        transcript.append(f"$ java -cp ... org.junit.runner.JUnitCore {class_name}Test")
        transcript.append(run_out.strip())

    print(f"[4/4] Writing evidence for {class_name} ...")
    log_path = OUT_DIR / f"run_log_{class_name}.txt"
    log_path.write_text("\n".join(transcript))
    png_path = OUT_DIR / f"evidence_{class_name}.png"
    render_evidence_png("\n".join(transcript), png_path, f"MDTE Engine run: {class_name}  (backend={backend_name})")

    status = "PASS" if ok and run_ok else "FAIL"
    print(f"      -> {class_name}: compile={'OK' if ok else 'FAIL'}, tests={'OK' if run_ok else 'FAIL'}  [{status}]")
    print(f"      -> log: {log_path}")
    print(f"      -> evidence image: {png_path}")
    return ok and run_ok


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("java_file", type=Path, help="Path to a single-class .java file")
    parser.add_argument("--backend", choices=["claude", "openai"], default="claude")
    parser.add_argument("--repair", type=int, default=1, help="Repair iterations on compile failure")
    args = parser.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    success = process(args.java_file.resolve(), args.backend, args.repair)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
