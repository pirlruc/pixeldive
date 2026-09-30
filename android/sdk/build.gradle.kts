import org.jetbrains.dokka.gradle.engine.parameters.VisibilityModifier

plugins {
    alias(libs.plugins.kotlin.jvm)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.kover)
    alias(libs.plugins.ktlint)
    alias(libs.plugins.detekt)
    alias(libs.plugins.dokka)
}

kotlin {
    jvmToolchain(17)
}

dependencies {
    implementation(libs.okhttp)
    implementation(libs.serialization.json)
    implementation(libs.coroutines.core)
    testImplementation(libs.okhttp.mockwebserver)
    testImplementation(libs.coroutines.test)
    testImplementation(libs.junit.jupiter)
    testRuntimeOnly(libs.junit.platform.launcher)
}

tasks.test {
    useJUnitPlatform()
    testLogging {
        events("passed", "skipped", "failed")
        exceptionFormat = org.gradle.api.tasks.testing.logging.TestExceptionFormat.FULL
    }
}

val statementFloor =
    (findProperty("pixeldive.statementCoverage") as String?)?.toIntOrNull() ?: 95
val branchFloor =
    (findProperty("pixeldive.branchCoverage") as String?)?.toIntOrNull() ?: 95

kover {
    reports {
        filters {
            excludes {
                // Wire DTOs: kotlinx.serialization + data-class copy/equals defaults
                // inflate branch counts without reflecting SDK logic (KT-TEST-002).
                classes(
                    "*\$\$serializer*",
                    "*\$Companion",
                    "*DeviceSnapshot",
                    "*JvmDeviceProbe",
                    "*DeviceProbe",
                )
                annotatedBy("kotlinx.serialization.Serializable")
            }
        }
        verify {
            rule {
                bound {
                    coverageUnits = kotlinx.kover.gradle.plugin.dsl.CoverageUnit.LINE
                    minValue = statementFloor
                }
                bound {
                    coverageUnits = kotlinx.kover.gradle.plugin.dsl.CoverageUnit.BRANCH
                    minValue = branchFloor
                }
            }
        }
    }
}

ktlint {
    android.set(false)
}

detekt {
    buildUponDefaultConfig = true
    allRules = false
    config.setFrom(files("$rootDir/config/detekt.yml"))
    source.setFrom(files("src/main/kotlin"))
    parallel = true
}

// KT-DOC-001: public API KDoc. reportUndocumented + failOnWarning is stricter
// than doc_coverage 95. HTML lands in build/dokka/html (not committed).
dokka {
    moduleName.set("pixeldive-sdk")
    dokkaSourceSets.main {
        includes.from("Module.md")
        documentedVisibilities.set(setOf(VisibilityModifier.Public))
        reportUndocumented.set(true)
        skipEmptyPackages.set(true)
        sourceLink {
            localDirectory.set(file("src/main/kotlin"))
            remoteUrl("https://github.com/pirlruc/pixeldive/tree/main/android/sdk/src/main/kotlin")
            remoteLineSuffix.set("#L")
        }
    }
    dokkaPublications.html {
        failOnWarning.set(true)
    }
}
