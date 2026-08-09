#!/usr/bin/env python3
"""
llm_test_engine.py - General-purpose LLM-based MDTE testing engine.
Given any single-class Java source file, this engine:
  1. Prompts an LLM to perform Input Space Partitioning (ISP) and Base Choice Coverage (BCC).
  2. Generates a compilable JUnit 4 test class from that artifact.
  3. Compiles the code, utilizing a single Generation-Validation-Repair loop on failure.
  4. Runs the compiled test and captures the pass/fail result.
"""
import argparse, os, re, subprocess, sys
from abc import ABC, abstractmethod
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIB_DIR, OUT_DIR = HERE / "lib", HERE / "out"
CLASSPATH_SEP = ";" if os.name == "nt" else ":"

class LLMBackend(ABC):
    @abstractmethod
    def complete(self, prompt: str) -> str: ...

class ClaudeCLIBackend(LLMBackend):
    """Calls the local `claude` CLI in non-interactive print mode."""
    def complete(self, prompt: str) -> str:
        result = subprocess.run(
            ["claude", "-p", prompt, "--allowedTools", ""],
            capture_output=True, text=True, timeout=180)
        if result.returncode != 0:
            raise RuntimeError(f"claude CLI failed: {result.stderr[:500]}")
        return result.stdout.strip()

class OpenAIBackend(LLMBackend):
    """Real OpenAI API backend. Requires `pip install openai` and an OPENAI_API_KEY."""
    def __init__(self, model: str = "gpt-4o"):
        from openai import OpenAI
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = model
        
    def complete(self, prompt: str) -> str:
        r = self.client.chat.completions.create(
            model=self.model, messages=[{"role": "user", "content": prompt}],
            temperature=0.2)
        return r.choices[0].message.content.strip()

class GeminiBackend(LLMBackend):
    """Real Google Gemini API backend. Requires `pip install google-genai` and GEMINI_API_KEY."""
    def __init__(self, model_name: str = "gemini-3.6-flash"):
        from google import genai
        from google.genai import types
        
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")
            
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        # Configure temperature to ensure deterministic, logical code generation
        self.config = types.GenerateContentConfig(temperature=0.2)

    def complete(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=self.config
        )
        return response.text.strip()

def get_backend(name: str) -> LLMBackend:
    backends = {
        "claude": ClaudeCLIBackend, 
        "openai": OpenAIBackend,
        "gemini": GeminiBackend
    }
    return backends[name]()

PROMPT_TEMPLATE = """You are a Software Quality Engineer applying Model-Driven Test Design (MDTD).
Analyze the Java class below and produce your answer in EXACTLY this format,
with no markdown code fences and no extra commentary outside the markers:

===ISP===
(List the Input Space Partitioning characteristics for each parameter, then
the Base Choice Coverage (BCC) test requirements: one base test choosing the
most "normal" block for every characteristic, then one test per characteristic
that varies ONLY that characteristic while holding the others at base.)
===JAVA===
(A complete, compilable JUnit 4 test class named {class_name}Test, importing
only org.junit.Test and org.junit.Assert.*, implementing every BCC requirement
as one @Test method each. The class under test, {class_name}, is already on
the classpath -- do not redefine it.)
===END===

Java source (file: {file_name}):
```java
{java_source}
```"""

REPAIR_TEMPLATE = """Your previous JUnit 4 test class failed to compile.
Compiler error:
{compile_error}
Previous code:
{previous_code}
Fix the class and respond again in EXACTLY the same ===ISP===/===JAVA===/===END===
format as before (ISP section may just say "unchanged"). No markdown fences."""

def build_prompt(java_file: Path) -> str:
    return PROMPT_TEMPLATE.format(
        class_name=java_file.stem, 
        file_name=java_file.name,
        java_source=java_file.read_text()
    )

def parse_response(text: str):
    isp_m = re.search(r"===ISP===(.*?)===JAVA===", text, re.DOTALL)
    java_m = re.search(r"===JAVA===(.*?)(===END===|$)", text, re.DOTALL)
    isp = isp_m.group(1).strip() if isp_m else "(ISP section not found)"
    code = java_m.group(1).strip() if java_m else text.strip()
    code = re.sub(r"^```(java)?\s*", "", code)
    code = re.sub(r"```\s*$", "", code).strip()
    return isp, code

def compile_test(class_name, target_java, out_dir):
    cp = CLASSPATH_SEP.join([str(LIB_DIR / "junit-4.13.2.jar"), str(LIB_DIR / "hamcrest-core-1.3.jar")])
    cmd = ["javac", "-cp", cp, "-d", str(out_dir), str(target_java), str(out_dir / f"{class_name}Test.java")]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr)

def run_test(class_name, out_dir):
    cp = CLASSPATH_SEP.join([str(LIB_DIR / "junit-4.13.2.jar"), str(LIB_DIR / "hamcrest-core-1.3.jar"), str(out_dir)])
    r = subprocess.run(["java", "-cp", cp, "org.junit.runner.JUnitCore", f"{class_name}Test"],
                        capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr)

def process(java_file: Path, backend_name: str, repair_budget: int = 1):
    class_name = java_file.stem
    backend = get_backend(backend_name)
    prompt = build_prompt(java_file)
    response = backend.complete(prompt)
    isp, java_code = parse_response(response)

    attempt, ok, compile_out = 0, False, ""
    while True:
        (OUT_DIR / f"{class_name}Test.java").write_text(java_code)
        ok, compile_out = compile_test(class_name, java_file, OUT_DIR)
        if ok or attempt >= repair_budget:
            break
        repair_prompt = REPAIR_TEMPLATE.format(compile_error=compile_out[:2000], previous_code=java_code)
        response = backend.complete(repair_prompt)
        isp, java_code = parse_response(response)
        attempt += 1

    run_ok, run_out = run_test(class_name, OUT_DIR) if ok else (False, "(skipped: compile failed)")
    return ok and run_ok, isp, compile_out, run_out

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("java_file", type=Path)
    parser.add_argument("--backend", choices=["claude", "openai", "gemini"], default="claude")
    parser.add_argument("--repair", type=int, default=1)
    args = parser.parse_args()
    
    OUT_DIR.mkdir(exist_ok=True)
    print(f"Starting MDTE Engine for {args.java_file.name} using {args.backend} backend...")
    success, isp, compile_out, run_out = process(args.java_file.resolve(), args.backend, args.repair)

    print("\n" + "="*40)
    print("=== 1. ISP & BCC RATIONALE ===")
    print("="*40)
    print(isp)

    print("\n" + "="*40)
    print("=== 2. COMPILATION OUTPUT ===")
    print("="*40)
    print(compile_out.strip() if compile_out.strip() else "Compilation successful. No errors.")

    print("\n" + "="*40)
    print("=== 3. JUNIT EXECUTION RESULTS ===")
    print("="*40)
    print(run_out.strip())
    print("="*40)

    if success:
        print("\n✅ SUCCESS: All tests compiled and passed!")
    else:
        print("\n❌ FAILURE: Tests failed to compile or run.")

    sys.exit(0 if success else 1)