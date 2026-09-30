# Verify activation, dependency versions, the nested module, and a saved app.
main <- function() {
  arguments <- commandArgs(TRUE)
  stopifnot(length(arguments) %in% c(2L, 3L))
  library <- normalizePath(arguments[[1]])
  release_directory <- normalizePath(arguments[[2]])

  if (length(arguments) == 3L) {
    check_project_activation(library)
  }
  .libPaths(c(library, .Library), include.site = FALSE)
  check_locked_packages(library, release_directory)
  check_builder_and_module(release_directory)
  check_exported_app(release_directory)
  cat("PASS: exact versions, isolated library, module, builder and exported app\n")
}

check_project_activation <- function(expected_library) {
  actual_library <- normalizePath(.libPaths()[[1]])
  if (actual_library != expected_library) {
    stop(sprintf(
      "Project activation failed: expected %s, got %s",
      expected_library, paste(.libPaths(), collapse = "; ")
    ))
  }
  stopifnot(identical(renv::settings$snapshot.type(), "all"))
  stopifnot(renv::status()$synchronized)
}

check_locked_packages <- function(library, release_directory) {
  lock <- jsonlite::read_json(file.path(release_directory, "renv.lock"))
  for (name in names(lock$Packages)) {
    actual_version <- packageDescription(name)$Version
    expected_version <- lock$Packages[[name]]$Version
    if (actual_version != expected_version) {
      stop(sprintf(
        "%s: expected %s, installed %s", name, expected_version, actual_version
      ))
    }
    stopifnot(startsWith(find.package(name), library))
  }
}

check_builder_and_module <- function(release_directory) {
  summary <- tb.modules::summarize_data(datasets::mtcars, "mpg")
  stopifnot(summary$n == 32L)
  stopifnot(inherits(
    tb.builder::run_app(release_directory), "shiny.appobj"
  ))
  shiny::testServer(
    tb.modules::module_server,
    args = list(column = shiny::reactive("mpg")),
    { stopifnot(result()$n == 32L) }
  )
}

check_exported_app <- function(release_directory) {
  export_directory <- tempfile("export-")
  on.exit(unlink(export_directory, recursive = TRUE), add = TRUE)
  tb.builder::export_app(export_directory, "hp", release_directory)
  original_lock <- read_lock_bytes(release_directory)
  exported_lock <- read_lock_bytes(export_directory)
  stopifnot(identical(original_lock, exported_lock))
  exported_app <- source(file.path(export_directory, "app.R"))$value
  stopifnot(inherits(exported_app, "shiny.appobj"))
}

read_lock_bytes <- function(directory) {
  readBin(file.path(directory, "renv.lock"), "raw", n = 1e7)
}

main()
