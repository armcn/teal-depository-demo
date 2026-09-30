# Bootstrap only renv. All application packages come from the lockfile.
bootstrap_renv <- function(version = "1.2.3") {
  # fs 2.x otherwise requires a separately installed libuv development library.
  # Build the bundled, pinned source so fresh Linux machines can restore too.
  Sys.setenv(USE_BUNDLED_LIBUV = "1")
  lib <- file.path(getwd(), ".work", "bootstrap")
  dir.create(lib, recursive = TRUE, showWarnings = FALSE)
  .libPaths(c(lib, .libPaths()))
  if ("renv" %in% loadedNamespaces() && as.character(getNamespaceVersion("renv")) != version) {
    stop("A different renv is already loaded. Restart with Rscript --vanilla.")
  }
  available <- tryCatch(suppressWarnings(utils::packageDescription("renv")$Version), error = function(e) NULL)
  if (identical(available, version) && requireNamespace("renv", quietly = TRUE)) {
    return(invisible(TRUE))
  }
  options(timeout = max(300L, getOption("timeout")))
  urls <- c(sprintf("https://cloud.r-project.org/src/contrib/renv_%s.tar.gz", version),
            sprintf("https://cloud.r-project.org/src/contrib/Archive/renv/renv_%s.tar.gz", version))
  tarball <- tempfile(fileext = ".tar.gz")
  on.exit(unlink(tarball), add = TRUE)
  for (url in urls) {
    success <- tryCatch(suppressWarnings(utils::download.file(url, tarball, quiet = TRUE)) == 0L,
                        error = function(e) FALSE)
    if (success) {
      utils::install.packages(tarball, repos = NULL, type = "source", lib = lib)
      if (requireNamespace("renv", quietly = TRUE) && as.character(packageVersion("renv")) == version) {
        return(invisible(TRUE))
      }
    }
  }
  stop("Could not install the pinned renv version")
}
