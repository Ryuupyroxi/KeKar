package com.ryuupyroxi.kekar.ui.leases

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.ryuupyroxi.kekar.domain.usecase.builtInLeaseTemplate

@Composable
fun LeasesScreen() {
    var body by remember { mutableStateOf(builtInLeaseTemplate()) }
    Column(Modifier.padding(16.dp).fillMaxWidth()) {
        OutlinedTextField(
            value = body,
            onValueChange = { body = it },
            label = { Text("Template") },
            modifier = Modifier.fillMaxWidth().heightIn(min = 180.dp)
        )
        Button(onClick = { body = builtInLeaseTemplate() }, Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
            Text("Load built-in template")
        }
    }
}
