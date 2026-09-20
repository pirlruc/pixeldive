package com.pixeldive.demo

import android.content.Context
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleOwner
import kotlinx.coroutines.suspendCancellableCoroutine
import java.util.concurrent.atomic.AtomicReference
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

/** CameraX preview + in-memory JPEG capture for gRPC upload. */
class CameraSession {
    private val capture = AtomicReference<ImageCapture?>(null)
    private val provider = AtomicReference<ProcessCameraProvider?>(null)
    private val appContext = AtomicReference<Context?>(null)

    fun bind(
        owner: LifecycleOwner,
        previewView: PreviewView,
    ) {
        val context = previewView.context.applicationContext
        appContext.set(context)
        val future = ProcessCameraProvider.getInstance(context)
        future.addListener(
            {
                val cameraProvider = future.get()
                provider.set(cameraProvider)
                val preview =
                    Preview.Builder().build().also { surface ->
                        surface.setSurfaceProvider(previewView.surfaceProvider)
                    }
                val imageCapture =
                    ImageCapture.Builder()
                        .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
                        .build()
                capture.set(imageCapture)
                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(
                    owner,
                    CameraSelector.DEFAULT_BACK_CAMERA,
                    preview,
                    imageCapture,
                )
            },
            ContextCompat.getMainExecutor(context),
        )
    }

    fun unbind() {
        provider.get()?.unbindAll()
        capture.set(null)
    }

    suspend fun takeJpeg(): ByteArray {
        val imageCapture = capture.get() ?: error("camera not bound")
        val context = appContext.get() ?: error("camera not bound")
        return suspendCancellableCoroutine { continuation ->
            imageCapture.takePicture(
                ContextCompat.getMainExecutor(context),
                object : ImageCapture.OnImageCapturedCallback() {
                    override fun onCaptureSuccess(image: ImageProxy) {
                        val bytes = jpegBytes(image)
                        image.close()
                        continuation.resume(bytes)
                    }

                    override fun onError(exception: ImageCaptureException) {
                        continuation.resumeWithException(exception)
                    }
                },
            )
        }
    }
}

internal fun jpegBytes(image: ImageProxy): ByteArray {
    val buffer = image.planes[0].buffer
    val bytes = ByteArray(buffer.remaining())
    buffer.get(bytes)
    return bytes
}
