pluginManagement {
    repositories {
        mavenCentral()
        google()
        gradlePluginPortal()
    }
}

plugins {
    id("org.gradle.toolchains.foojay-resolver-convention") version "0.9.0"
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        mavenCentral()
        google()
    }
}

rootProject.name = "pixeldive-android"

include(":sdk")

// GitHub-hosted Ubuntu sets ANDROID_HOME; that must not pull in Compose/AGP.
// Android Studio writes local.properties. Opt in with PIXELDIVE_INCLUDE_ANDROID_DEMO=1.
val includeDemo =
    System.getenv("PIXELDIVE_INCLUDE_ANDROID_DEMO") == "1" ||
        file("local.properties").isFile
if (includeDemo) {
    include(":demo")
}
