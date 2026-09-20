package com.pixeldive.demo

import android.app.Application
import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pixeldive.sdk.DeviceSnapshot
import com.pixeldive.sdk.PixeldiveClient
import com.pixeldive.sdk.SessionImage
import com.pixeldive.sdk.SessionRead
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/** UI state for the capture demo. All service calls go through [PixeldiveClient]. */
class DemoViewModel(
    private val application: Application,
) : ViewModel() {
    private val _state = MutableStateFlow(DemoState())
    val state: StateFlow<DemoState> = _state

    fun onBaseUrl(value: String) {
        _state.update { it.copy(baseUrl = value) }
    }

    fun onToken(value: String) {
        _state.update { it.copy(token = value) }
    }

    fun createSession() {
        run("create session") { client ->
            val payload =
                DeviceSnapshot.current(
                    sessionName = "android-demo-${System.currentTimeMillis()}",
                    probe = AndroidDeviceProbe(application),
                )
            val created = client.createSession(payload)
            _state.update { it.copy(selected = created, log = "Created ${created.id}") }
            refresh(client)
        }
    }

    fun refresh() {
        run("refresh") { client ->
            refresh(client)
            _state.update { it.copy(log = "Listed ${it.sessions.size} sessions") }
        }
    }

    fun upload(uri: Uri) {
        val session = _state.value.selected
        if (session == null) {
            _state.update { it.copy(log = "Create or select a session first.") }
            return
        }
        run("upload") { client ->
            val bytes = application.contentResolver.openInputStream(uri)?.use { it.readBytes() }
                ?: error("unable to read picked image")
            val type = application.contentResolver.getType(uri) ?: "image/jpeg"
            val name = if (type == "image/png") "frame.png" else "frame.jpg"
            val image = client.uploadImage(session.id.toString(), name, bytes, type)
            _state.update { it.copy(log = "Uploaded ${image.filename} (${image.sizeBytes} bytes)") }
            refresh(client)
        }
    }

    fun downloadFirst() {
        val session = _state.value.selected
        val image = _state.value.images.firstOrNull()
        if (session == null || image == null) {
            _state.update { it.copy(log = "No image to download.") }
            return
        }
        run("download") { client ->
            val bytes = client.downloadImage(session.id.toString(), image.id.toString())
            _state.update { it.copy(log = "Downloaded ${bytes.size} bytes") }
        }
    }

    fun deleteSelected() {
        val session = _state.value.selected
        if (session == null) {
            _state.update { it.copy(log = "No session selected.") }
            return
        }
        run("delete") { client ->
            client.deleteSession(session.id.toString())
            _state.update { it.copy(selected = null, images = emptyList(), log = "Deleted session") }
            refresh(client)
        }
    }

    private suspend fun refresh(client: PixeldiveClient) {
        val page = client.listSessions(limit = 20)
        val selected = _state.value.selected ?: page.items.firstOrNull()
        val images =
            if (selected != null) {
                client.listImages(selected.id.toString()).items
            } else {
                emptyList()
            }
        _state.update {
            it.copy(sessions = page.items, selected = selected, images = images)
        }
    }

    private fun run(
        label: String,
        body: suspend (PixeldiveClient) -> Unit,
    ) {
        viewModelScope.launch {
            _state.update { it.copy(busy = true) }
            try {
                body(makeClient())
            } catch (exc: Exception) {
                _state.update { it.copy(log = "$label failed: ${exc.message}") }
            } finally {
                _state.update { it.copy(busy = false) }
            }
        }
    }

    private fun makeClient(): PixeldiveClient {
        val trimmed = _state.value.token.trim()
        return PixeldiveClient(
            baseUrl = _state.value.baseUrl,
            token = trimmed.ifEmpty { null },
        )
    }

    companion object {
        fun factory(application: Application): ViewModelProvider.Factory =
            object : ViewModelProvider.Factory {
                @Suppress("UNCHECKED_CAST")
                override fun <T : ViewModel> create(modelClass: Class<T>): T =
                    DemoViewModel(application) as T
            }
    }
}

data class DemoState(
    val baseUrl: String = "http://10.0.2.2:8000",
    val token: String = "",
    val log: String = "Ready.",
    val sessions: List<SessionRead> = emptyList(),
    val images: List<SessionImage> = emptyList(),
    val selected: SessionRead? = null,
    val busy: Boolean = false,
) {
    val selectedLabel: String
        get() {
            val session = selected ?: return "Selected: none"
            return "Selected: ${session.sessionName} (${session.phoneInfo.model})"
        }
    val imageCount: Int get() = images.size
}
