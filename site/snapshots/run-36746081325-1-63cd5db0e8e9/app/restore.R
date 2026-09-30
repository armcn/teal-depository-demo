# This file is delivered with every downloaded app and tested directly by CI.
source("bootstrap.R")

restore_release_app <- function() {
  bootstrap_renv()
  require_release_r_version()
  configure_project_restore()
  restore_project_library()
  configure_release_snapshot_policy()
  renv::activate(project = getwd())
  cat("Restored this app's release. Restart R, then run shiny::runApp().\n")
}

require_release_r_version <- function() {
  required_version <- renv::lockfile_read("renv.lock")$R$Version
  if (as.character(getRversion()) != required_version) {
    stop(sprintf("This release requires R %s", required_version))
  }
}

configure_project_restore <- function() {
  options(timeout = 300)
  Sys.setenv(
    RENV_CONFIG_CACHE_ENABLED = "FALSE",
    RENV_CONFIG_AUTOLOADER_ENABLED = "TRUE"
  )
}

restore_project_library <- function() {
  library <- renv::paths$library(project = getwd())
  dir.create(library, recursive = TRUE, showWarnings = FALSE)
  renv::restore(
    project = getwd(), lockfile = "renv.lock",
    library = library, prompt = FALSE
  )
}

configure_release_snapshot_policy <- function() {
  # Exports deliberately retain the complete tested package cohort.
  renv::settings$snapshot.type("all", project = getwd())
  locked_packages <- names(renv::lockfile_read("renv.lock")$Packages)
  bundled_packages <- rownames(utils::installed.packages(
    lib.loc = .Library, priority = "recommended"
  ))
  # R's unused bundled packages are outside the app's locked dependency cohort.
  renv::settings$ignored.packages(
    setdiff(bundled_packages, locked_packages), project = getwd()
  )
}

restore_release_app()
