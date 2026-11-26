package com.ryuupyroxi.kekar.ui.applicants

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.ryuupyroxi.kekar.domain.model.Applicant

@Composable
fun ApplicantsScreen(applicants: List<Applicant>) {
    LazyColumn(Modifier.padding(16.dp).fillMaxWidth()) {
        items(applicants) { applicant ->
            Card(Modifier.padding(vertical = 4.dp)) {
                Text("${applicant.name} — ${applicant.stage}", Modifier.padding(16.dp))
            }
        }
    }
}
