# Quarto Live (development version)

# Quarto Live 0.1.2

## New features

* Setup blocks may now be attached to multiple exercises by providing a list for the `exercise` cell option.

* Reveal.js slides containing live cells are now automatically made scrollable (#67).

## Breaking changes

* Previously the cell option `autorun` defaulted to `true` for "sandbox" type cells, but `false` for exercises. This has been found to be confusing, and so `autorun: false` is now always the default state. Autorun may still be enabled by setting the cell option directly, or set document-wide using the `cell-options` YAML header.

* The Pyodide execution engine has been upgraded to version 0.27.0.

## Bug fixes

* Ensure that JavaScript scripts that have been dynamically added via HTML output are executed.

* Fixed building deep subdirectory structure when copying resources into the WebAssembly virtual filesystem (#53).

* Fixed layering of shared execution environments in Pyodide exercises (#63).

* Ensure variables defined at the top level of the the grading environment are available as globals when executing grading algorithms with Pyodide (#63).

* Better handle `echo: false` and `include: false` cell options (#62).

* Fixed applying the `completion` cell option to `pyodide` cells (#2).

* Avoid interpreting Python cell text output as HTML (#69).

* Fixed grading of R user code with multiple trailing newlines (#77).

* Fixed Plotly and matplotlib figures on Pyodide v0.27.0 (#79, #80).

# Quarto Live 0.1.1

Initial release.
