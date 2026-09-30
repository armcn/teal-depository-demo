args <- commandArgs(TRUE)
stopifnot(length(args) == 2L)
.libPaths(c(normalizePath(args[[1]]), .Library), include.site = FALSE)
release_dir <- normalizePath(args[[2]])
lock <- jsonlite::read_json(file.path(release_dir, "renv.lock"))
for (name in names(lock$Packages)) {
  actual <- packageDescription(name)$Version
  expected <- lock$Packages[[name]]$Version
  if (actual != expected) stop(sprintf("%s: expected %s, installed %s", name, expected, actual))
  stopifnot(startsWith(find.package(name), normalizePath(args[[1]])))
}
stopifnot(tb.modules::summarize_data(datasets::mtcars, "mpg")$n == 32L)
stopifnot(inherits(tb.builder::run_app(release_dir), "shiny.appobj"))
shiny::testServer(tb.modules::module_server, args = list(column = shiny::reactive("mpg")), {
  stopifnot(result()$n == 32L)
})
export <- tempfile("export-")
tb.builder::export_app(export, "hp", release_dir)
stopifnot(identical(readBin(file.path(export, "renv.lock"), "raw", n = 1e7),
                    readBin(file.path(release_dir, "renv.lock"), "raw", n = 1e7)))
stopifnot(inherits(source(file.path(export, "app.R"))$value, "shiny.appobj"))
unlink(export, recursive = TRUE)
cat("PASS: exact versions, isolated library, module, builder and exported app\n")
