source("bootstrap.R")
bootstrap_renv()
required_r <- renv::lockfile_read("renv.lock")$R$Version
if (as.character(getRversion()) != required_r) stop(sprintf("This release requires R %s", required_r))
options(timeout = 300)
Sys.setenv(RENV_CONFIG_CACHE_ENABLED = "FALSE")
renv::restore(project = getwd(), lockfile = "renv.lock", prompt = FALSE)
renv::activate(project = getwd())
cat("Restored this app's release. Restart R, then run shiny::runApp().\n")
