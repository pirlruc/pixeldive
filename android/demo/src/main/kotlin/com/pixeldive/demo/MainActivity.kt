package com.pixeldive.demo

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.lifecycle.compose.collectAsStateWithLifecycle

class MainActivity : ComponentActivity() {
    private val model: DemoViewModel by viewModels { DemoViewModel.factory(application) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                DemoScreen(model)
            }
        }
    }
}

@Composable
private fun DemoScreen(model: DemoViewModel) {
    val state by model.state.collectAsStateWithLifecycle()
    val picker =
        rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
            if (uri != null) {
                model.upload(uri)
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
        OutlinedTextField(
            value = state.baseUrl,
            onValueChange = model::onBaseUrl,
            label = { Text("Base URL") },
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
        Button(onClick = { model.refresh() }, enabled = !state.busy) {
            Text("Refresh sessions")
        }
        Button(onClick = { model.createSession() }, enabled = !state.busy) {
            Text("Create Android session")
        }
        Text(state.selectedLabel)
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
