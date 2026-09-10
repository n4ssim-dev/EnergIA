
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-prediction',
  standalone: true,
  imports: [
    FormsModule,
    CommonModule
  ],
  templateUrl: './prediction.html',
  styleUrl: './prediction.scss'
})
export class Prediction {

  region = '';
  date = '';
  heure = '';

  prediction: number | null = null;

  confidence = 94;


  predire() {

    if (!this.region || !this.date || !this.heure) {
      return;
    }

    // Simulation temporaire
    this.prediction = Math.floor(
      3000 + Math.random() * 2000
    );
  }

}