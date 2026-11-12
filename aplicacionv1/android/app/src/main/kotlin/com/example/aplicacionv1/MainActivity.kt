package com.example.aplicacionv1

import android.app.Activity
import android.content.Intent
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.ByteArrayOutputStream

class MainActivity : FlutterActivity() {
    private var pending: MethodChannel.Result? = null
    private var bytes: ByteArray? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "exb/files")
            .setMethodCallHandler { call, result ->
                if (pending != null) {
                    result.error("busy", "Ya hay un selector de archivos abierto.", null)
                } else if (call.method == "save" || call.method == "pickWorkbook") {
                    val save = call.method == "save"
                    bytes = if (save) call.argument<ByteArray>("bytes") else null
                    val intent = Intent(if (save) Intent.ACTION_CREATE_DOCUMENT else Intent.ACTION_OPEN_DOCUMENT)
                        .addCategory(Intent.CATEGORY_OPENABLE)
                        .setType(if (save) call.argument<String>("mime") ?: "application/octet-stream" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                    if (save) intent.putExtra(Intent.EXTRA_TITLE, call.argument<String>("filename"))
                    pending = result
                    try {
                        startActivityForResult(intent, if (save) 5101 else 5102)
                    } catch (error: Exception) {
                        pending = null
                        bytes = null
                        result.error("files", "No se pudo abrir el selector de archivos.", null)
                    }
                } else result.notImplemented()
            }
    }

    @Deprecated("Activity result bridge for the Flutter file channel")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != 5101 && requestCode != 5102) return
        val result = pending ?: return
        val content = bytes
        pending = null
        bytes = null
        val uri = data?.data
        if (resultCode != Activity.RESULT_OK || uri == null) {
            result.success(null)
            return
        }
        try {
            if (requestCode == 5101) {
                contentResolver.openOutputStream(uri)?.use { it.write(content ?: byteArrayOf()) }
                    ?: throw IllegalStateException("No se pudo guardar el archivo")
                result.success(true)
            } else {
                val output = ByteArrayOutputStream()
                contentResolver.openInputStream(uri)?.use { input ->
                    val buffer = ByteArray(65536)
                    while (true) {
                        val count = input.read(buffer)
                        if (count < 0) break
                        if (output.size() + count > 20 * 1024 * 1024) throw IllegalArgumentException("El Excel supera 20 MB")
                        output.write(buffer, 0, count)
                    }
                } ?: throw IllegalStateException("No se pudo leer el archivo")
                result.success(output.toByteArray())
            }
        } catch (error: Exception) {
            result.error("files", error.message ?: "No se pudo procesar el archivo.", null)
        }
    }
}
