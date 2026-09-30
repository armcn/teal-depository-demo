# Bootstrap only renv. Application packages come from the release lockfile.
bootstrap_renv <- function(version = "1.2.3") {
  configure_source_builds()
  library <- prepare_bootstrap_library()
  require_compatible_loaded_renv(version)
  if (renv_version_available(version)) {
    return(invisible(TRUE))
  }
  install_pinned_renv(version, library)
}

configure_source_builds <- function() {
  # Use fs's bundled libuv instead of an undeclared system development library.
  Sys.setenv(USE_BUNDLED_LIBUV = "1")
  options(timeout = max(300L, getOption("timeout")))
}

prepare_bootstrap_library <- function() {
  library <- file.path(getwd(), ".work", "bootstrap")
  dir.create(library, recursive = TRUE, showWarnings = FALSE)
  .libPaths(c(library, .libPaths()))
  library
}

require_compatible_loaded_renv <- function(version) {
  if ("renv" %in% loadedNamespaces()) {
    loaded_version <- as.character(getNamespaceVersion("renv"))
    if (loaded_version != version) {
      stop("A different renv is already loaded. Restart with Rscript --vanilla.")
    }
  }
}

renv_version_available <- function(version) {
  installed_version <- tryCatch(
    suppressWarnings(utils::packageDescription("renv")$Version),
    error = function(error) NULL
  )
  identical(installed_version, version) &&
    requireNamespace("renv", quietly = TRUE)
}

install_pinned_renv <- function(version, library) {
  archive <- tempfile(fileext = ".tar.gz")
  on.exit(unlink(archive), add = TRUE)
  for (url in renv_archive_urls(version)) {
    if (!download_renv_archive(url, archive)) {
      next
    }
    utils::install.packages(
      archive, repos = NULL, type = "source", lib = library
    )
    if (renv_version_available(version)) {
      return(invisible(TRUE))
    }
  }
  stop("Could not install the pinned renv version")
}

renv_archive_urls <- function(version) {
  filename <- sprintf("renv_%s.tar.gz", version)
  repository <- "https://cloud.r-project.org/src/contrib"
  c(
    paste(repository, filename, sep = "/"),
    paste(repository, "Archive/renv", filename, sep = "/")
  )
}

download_renv_archive <- function(url, destination) {
  tryCatch(
    suppressWarnings(
      utils::download.file(url, destination, quiet = TRUE)
    ) == 0L,
    error = function(error) FALSE
  )
}
