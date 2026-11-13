# Module pixeldive-sdk

Kotlin JVM client for the pixeldive session service. REST uses OkHttp. Image
bytes use OkHttp HTTP/2 prior knowledge (h2c).

# Package com.pixeldive.sdk

Public types are the REST client, the gRPC image client, session wire models,
device snapshot helpers, and Camera2 label mapping. Transport helpers in this
package are `internal`.
