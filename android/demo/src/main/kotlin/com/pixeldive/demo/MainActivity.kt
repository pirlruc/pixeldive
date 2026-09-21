package com.pixeldive.demo

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.camera.view.PreviewView
import androidx.lifecycle.LifecycleOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import kotlinx.coroutines.delay

class MainActivity : ComponentActivity() {
    private val model: DemoViewModel by viewModels { DemoViewModel.factory(application) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                DemoScreen(model, this)
            }
        }
    }
}

@Composable
private fun DemoScreen(
    model: DemoViewModel,
    owner: LifecycleOwner,
) {
    val state by model.state.collectAsStateWithLifecycle()
    val camera = remember { CameraSession() }
    val picker =
        rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
            if (uri != null) {
                model.upload(uri)
            }
        }
    val permission =
        rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (granted) {
                model.setCapturing(true)
            } else {
                model.onCameraDenied()
            }
        }
    Column(
        modifier =
            Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Pixeldive", style = MaterialTheme.typography.headlineSmall)
        serviceFields(state, model)
        Button(onClick = { model.refresh() }, enabled = !state.busy) {
            Text("Refresh sessions")
        }
        Button(onClick = { model.createSession() }, enabled = !state.busy) {
            Text("Create Android session")
        }
        Text(state.selectedLabel)
        cameraBlock(state, model, owner, camera, permission)
        Button(
            onClick = {
                picker.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
            },
            enabled = !state.busy,
        ) {
            Text("Upload from photos")
        }
        Button(onClick = { model.downloadFirst() }, enabled = !state.busy) {
            Text("Download first image")
        }
        Button(onClick = { model.deleteSelected() }, enabled = !state.busy) {
            Text("Delete selected")
        }
        Text("${state.imageCount} image(s)")
        Text(
            state.log,
            fontFamily = FontFamily.Monospace,
            style = MaterialTheme.typography.bodySmall,
        )
    }
}

@Composable
private fun serviceFields(
    state: DemoState,
    model: DemoViewModel,
) {
    OutlinedTextField(
        value = state.baseUrl,
        onValueChange = model::onBaseUrl,
        label = { Text("REST URL") },
        modifier = Modifier.fillMaxWidth(),
        enabled = !state.busy,
    )
    OutlinedTextField(
        value = state.grpcHost,
        onValueChange = model::onGrpcHost,
        label = { Text("gRPC host") },
        modifier = Modifier.fillMaxWidth(),
        enabled = !state.busy,
    )
    OutlinedTextField(
        value = state.grpcPort,
        onValueChange = model::onGrpcPort,
        label = { Text("gRPC port") },
        modifier = Modifier.fillMaxWidth(),
        enabled = !state.busy,
    )
    OutlinedTextField(
        value = state.token,
        onValueChange = model::onToken,
        label = { Text("Bearer token (optional)") },
        visualTransformation = PasswordVisualTransformation(),
        modifier = Modifier.fillMaxWidth(),
        enabled = !state.busy,
    )
}

@Composable
private fun cameraBlock(
    state: DemoState,
    model: DemoViewModel,
    owner: LifecycleOwner,
    camera: CameraSession,
    permission: ActivityResultLauncher<String>,
) {
    val context = LocalContext.current
    if (state.capturing) {
        AndroidView(
            modifier =
                Modifier
                    .fillMaxWidth()
                    .height(220.dp),
            factory = { viewContext ->
                PreviewView(viewContext).also { preview -> camera.bind(owner, preview) }
            },
        )
        DisposableEffect(camera) {
            onDispose { camera.unbind() }
        }
        LaunchedEffect(state.capturing) {
            while (model.state.value.capturing) {
                if (!model.state.value.uploading) {
                    try {
                        model.uploadFrame(camera.takeJpeg())
                    } catch (exc: Exception) {
                        model.onFrameError(exc)
                    }
                }
                delay(450)
            }
        }
        Button(onClick = { model.setCapturing(false) }) {
            Text("Stop camera")
        }
    } else {
        Button(
            onClick = {
                if (state.selected == null) {
                    model.needSession()
                    return@Button
                }
                val granted =
                    ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) ==
                        PackageManager.PERMISSION_GRANTED
                if (granted) {
                    model.setCapturing(true)
                } else {
                    permission.launch(Manifest.permission.CAMERA)
                }
            },
            enabled = !state.busy,
        ) {
            Text("Start camera feed")
        }
    }
}
