# Multi Trace Open Command

This is the design doc for extending the `torq open` command
to support a list of trace files or a directory path containing
multiple trace files.

When `torq open` is executed with multiple traces, it should
verify the traces are there and should proceed to launch an interactive
query REPL, where the CLI user can write a PerfettoSQL query and the
output of the query will be printed to the screen.


## BatchTraceProcessor

The tool to execute a query on multiple traces will be Perfetto's
BatchTraceProcessor.

Batch Trace Processor is part of the perfetto Python library and can be installed by running:

```bash
pip3 install pandas       # prerequisite for Batch Trace Processor
pip3 install perfetto
```

**Note:** As this project uses Bazel, ensure dependencies are added to `MODULE.bazel` or the appropriate build files.

To load traces, the simplest way to load traces in is by passing a list of file paths to load:

```python
from perfetto.batch_trace_processor.api import BatchTraceProcessor

files = [
  'traces/slow-start.pftrace',
  'traces/oom.pftrace',
  'traces/high-battery-drain.pftrace',
]
with BatchTraceProcessor(files) as btp:
  btp.query('...')
```

glob can be used to load all traces in a directory:

```python
from perfetto.batch_trace_processor.api import BatchTraceProcessor

files = glob.glob('traces/*.pftrace')
with BatchTraceProcessor(files) as btp:
  btp.query('...')
```

Writing queries with batch trace processor works very similarly to the Python API.

For example, to get a count of the number of userspace slices:

```
>>> btp.query('select count(1) from slice')
[  count(1)
0  2092592,   count(1)
0   156071,   count(1)
0   121431]
```
The return value of query is a list of Pandas dataframes, one for each trace loaded.

A common requirement is for all of the traces to be flattened into a single dataframe instead of getting one dataframe per-trace. To support this, the query_and_flatten function can be used:

```
>>> btp.query_and_flatten('select count(1) from slice')
  count(1)
0  2092592
1   156071
2   121431
```

query_and_flatten also implicitly adds columns indicating the originating trace. The exact columns added depend on the resolver being used: consult your resolver's documentation for more information.

## Torq open command

The `torq open` command will be updated to accept one or more file paths or directory paths.

**Usage:**

```bash
torq open [file_path [file_path ...]]
```

### Supported Arguments

-   `file_path`: (Required) One or more paths to trace files or directories containing trace files.
    -   **Single Trace Found:** If the collection of traces (from all provided files and directories) contains **exactly one** file, Torq opens it in the Perfetto UI (standard behavior).
    -   **Multiple Traces Found:** If the collection contains **more than one** file, Torq launches the interactive BatchTraceProcessor REPL.

### Trace Collection Logic

Torq will iterate through all provided `file_path` arguments to collect a list of valid trace files (e.g., `.pftrace`, `.perfetto-trace`):
1.  **Direct Files:** If an argument is a file, it is added to the collection.
2.  **Directories:** If an argument is a directory, Torq scans it non-recursively for valid trace files and adds all found files to the collection.

The final execution mode is determined by the total number of traces collected:
-   **1 trace:** Opens in Perfetto UI.
-   **> 1 trace:** Launches interactive BTP REPL.
-   **0 traces:** Returns a validation error.

### Interactive REPL Mode

When multiple traces are detected, Torq transitions into an interactive SQL environment powered by `BatchTraceProcessor`.

#### Behavior
-   **Trace Loading:** Displays a loading message indicating the number of traces being processed.
-   **Prompt:** Provides a persistent `> ` prompt for user input.
-   **Query Execution:** Executes the provided PerfettoSQL query across all loaded traces.
-   **Output:** Prints the results as a unified table. By default, it uses `query_and_flatten` to provide a consolidated view with trace identification columns.
-   **Session Control:** Users can exit the REPL using `exit`, `quit`, `Ctrl-D`, or `Ctrl-C`.

#### Internal Implementation
1.  **Initialization:** The REPL will be implemented as a specialized command executor. It will initialize a `BatchTraceProcessor` instance with the collected file list.
2.  **Input Loop:** A `while` loop will capture user input. For improved UX, the `readline` module should be used to support command history and basic line editing. Catching `KeyboardInterrupt` (`Ctrl-C`) or `EOFError` (`Ctrl-D`) will gracefully exit the session.
3.  **Command Parsing:** Basic checks for "exit" or "quit" commands before treating the input as a SQL query.
4.  **Error Handling:** SQL syntax errors or execution failures within `btp.query_and_flatten` will be caught and printed to `stderr` without crashing the REPL session.

#### Example Session
```bash
$ torq open ./slow_run_traces/
Loading 3 traces into BatchTraceProcessor...
[torq REPL] - Type 'quit' to exit.
> select count(1) as total_slices from slice
   total_slices
0       2092592
1        156071
2        121431
> select name, dur from slice order by dur desc limit 2
                   name        dur
0  actual_frame_timeline  105672344
1  actual_frame_timeline   98234122
> quit
Exiting torq REPL.
```

### Rejected Commands & Error Handling

To ensure a robust developer experience, the following cases will be rejected with clear error messages and suggestions:

**1. Invalid file or directory path:**
```bash
torq open non_existent_path
```
*Error:* `Command is invalid because 'non_existent_path' is not a valid file or directory path.`
*Suggestion:* `Make sure the path exists.`

**2. Mixed valid and invalid paths:**
```bash
torq open trace1.pftrace non_existent_path
```
*Error:* `Command is invalid because 'non_existent_path' is not a valid file or directory path.`
*Suggestion:* `Make sure the path exists.`
*Rationale:* Fails fast to ensure the user is aware of the missing data before starting a analysis session.

**3. Empty directory or directory with no valid traces:**
```bash
torq open ./empty_dir
```
*Error:* `Command is invalid because no valid trace files were found in the provided paths.`
*Suggestion:* `Make sure the provided paths contain at least one valid trace file (e.g. .pftrace, .perfetto-trace).`

**4. Unsupported file types:**
```bash
torq open image.png
```
*Error:* `Command is invalid because 'image.png' is not a supported trace file format.`
*Suggestion:* `Provide a path to a supported trace file format (e.g. .pftrace, .perfetto-trace).`

**5. No arguments provided:**
```bash
torq open
```
*Error:* `torq open: error: the following arguments are required: file_path` (Standard argparse error).

## Project milestones

The implementation of the multi-trace open command will be executed in the following order:

### 1. Dependency Management
-   **Objective:** Ensure `pandas` and `perfetto` Python libraries are available in the Torq environment via Bazel.
-   **Tasks:**
    -   Update `MODULE.bazel` (or equivalent build files) to include `pandas` and `perfetto` as dependencies.
    -   Verify the dependencies are correctly fetched and importable in the Torq source code.

### 2. Argument Parsing & Validation
-   **Objective:** Update the `torq open` command to accept multiple arguments and enforce validation rules.
-   **Tasks:**
    -   Modify `add_open_parser` in `src/open.py` to change `file_path` `nargs` to `+` (one or more).
    -   Update `verify_open_args` to iterate through all provided paths.
    -   Implement validation logic to reject invalid paths, empty directories, and unsupported file types with the specified error messages.
    -   Add unit tests for all valid and invalid argument scenarios.

### 3. Trace Collection Logic
-   **Objective:** Implement the logic to scan directories and collect all valid trace files.
-   **Tasks:**
    -   Create a helper function (e.g., `collect_traces`) that takes the list of input paths.
    -   Implement the logic to distinguish between files and directories.
    -   Implement non-recursive directory scanning for `.pftrace` and `.perfetto-trace` files.
    -   Return a consolidated list of unique file paths.
    -   Unit test the collection logic with various file/directory combinations.

### 4. Interactive REPL Implementation
-   **Objective:** Build the interactive SQL shell powered by `BatchTraceProcessor`.
-   **Tasks:**
    -   Create a new class or function (e.g., `BatchTraceRepl`) to handle the interactive session.
    -   Initialize `BatchTraceProcessor` with the collected trace files.
    -   Implement the `while` loop for user input, integrating `readline` for history support.
    -   Implement the "exit", "quit", "Ctrl-D", and "Ctrl-C" handling.
    -   Execute queries using `btp.query_and_flatten()` and print the results using Pandas' string formatting.
    -   Implement error handling for SQL errors to prevent crashing the REPL.
    -   Integrate this new mode into `execute_open_command` in `src/open.py`, triggering it only when multiple traces are collected.
