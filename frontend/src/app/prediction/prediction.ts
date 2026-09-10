
import { Component, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { PredictionService } from '../prediction-service';
import { HttpClient } from '@angular/common/http';

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
export class Prediction implements OnInit{
     
constructor(private predictionService : PredictionService, private http: HttpClient) { }; 

  inputIdRegion ='';
  inputHeure ='';
  inputDate ='';


  date = '';
  heure = signal<any>(null);
  regions = signal<any>(null);

  prediction: number | null = null;

  confidence = 94;

  quartsHeures = signal([
  { id: '00:00', name: '00:00' },
  { id: '00:15', name: '00:15' },
  { id: '00:30', name: '00:30' },
  { id: '00:45', name: '00:45' },

  { id: '01:00', name: '01:00' },
  { id: '01:15', name: '01:15' },
  { id: '01:30', name: '01:30' },
  { id: '01:45', name: '01:45' },

  { id: '02:00', name: '02:00' },
  { id: '02:15', name: '02:15' },
  { id: '02:30', name: '02:30' },
  { id: '02:45', name: '02:45' },

  { id: '03:00', name: '03:00' },
  { id: '03:15', name: '03:15' },
  { id: '03:30', name: '03:30' },
  { id: '03:45', name: '03:45' },

  { id: '04:00', name: '04:00' },
  { id: '04:15', name: '04:15' },
  { id: '04:30', name: '04:30' },
  { id: '04:45', name: '04:45' },

  { id: '05:00', name: '05:00' },
  { id: '05:15', name: '05:15' },
  { id: '05:30', name: '05:30' },
  { id: '05:45', name: '05:45' },

  { id: '06:00', name: '06:00' },
  { id: '06:15', name: '06:15' },
  { id: '06:30', name: '06:30' },
  { id: '06:45', name: '06:45' },

  { id: '07:00', name: '07:00' },
  { id: '07:15', name: '07:15' },
  { id: '07:30', name: '07:30' },
  { id: '07:45', name: '07:45' },

  { id: '08:00', name: '08:00' },
  { id: '08:15', name: '08:15' },
  { id: '08:30', name: '08:30' },
  { id: '08:45', name: '08:45' },

  { id: '09:00', name: '09:00' },
  { id: '09:15', name: '09:15' },
  { id: '09:30', name: '09:30' },
  { id: '09:45', name: '09:45' },

  { id: '10:00', name: '10:00' },
  { id: '10:15', name: '10:15' },
  { id: '10:30', name: '10:30' },
  { id: '10:45', name: '10:45' },

  { id: '11:00', name: '11:00' },
  { id: '11:15', name: '11:15' },
  { id: '11:30', name: '11:30' },
  { id: '11:45', name: '11:45' },

  { id: '12:00', name: '12:00' },
  { id: '12:15', name: '12:15' },
  { id: '12:30', name: '12:30' },
  { id: '12:45', name: '12:45' },

  { id: '13:00', name: '13:00' },
  { id: '13:15', name: '13:15' },
  { id: '13:30', name: '13:30' },
  { id: '13:45', name: '13:45' },

  { id: '14:00', name: '14:00' },
  { id: '14:15', name: '14:15' },
  { id: '14:30', name: '14:30' },
  { id: '14:45', name: '14:45' },

  { id: '15:00', name: '15:00' },
  { id: '15:15', name: '15:15' },
  { id: '15:30', name: '15:30' },
  { id: '15:45', name: '15:45' },

  { id: '16:00', name: '16:00' },
  { id: '16:15', name: '16:15' },
  { id: '16:30', name: '16:30' },
  { id: '16:45', name: '16:45' },

  { id: '17:00', name: '17:00' },
  { id: '17:15', name: '17:15' },
  { id: '17:30', name: '17:30' },
  { id: '17:45', name: '17:45' },

  { id: '18:00', name: '18:00' },
  { id: '18:15', name: '18:15' },
  { id: '18:30', name: '18:30' },
  { id: '18:45', name: '18:45' },

  { id: '19:00', name: '19:00' },
  { id: '19:15', name: '19:15' },
  { id: '19:30', name: '19:30' },
  { id: '19:45', name: '19:45' },

  { id: '20:00', name: '20:00' },
  { id: '20:15', name: '20:15' },
  { id: '20:30', name: '20:30' },
  { id: '20:45', name: '20:45' },

  { id: '21:00', name: '21:00' },
  { id: '21:15', name: '21:15' },
  { id: '21:30', name: '21:30' },
  { id: '21:45', name: '21:45' },

  { id: '22:00', name: '22:00' },
  { id: '22:15', name: '22:15' },
  { id: '22:30', name: '22:30' },
  { id: '22:45', name: '22:45' },

  { id: '23:00', name: '23:00' },
  { id: '23:15', name: '23:15' },
  { id: '23:30', name: '23:30' },
  { id: '23:45', name: '23:45' }
]);
  
  ngOnInit(): void {
    this.listRegions();
  }
 
    listRegions(): void {
    this.predictionService.getRegions().subscribe({
      next: (res) => {
        this.regions.set(res.reponse.regions);

        console.log(res.reponse.regions);
      },
      error: (err) => {
        console.error('Erreur :', err);
      }
    });
  }




  predire() {

    if (!this.inputIdRegion || !this.inputDate || !this.inputHeure) {
      return;
    }
    // Simulation temporaire
    this.prediction = Math.floor(
      3000 + Math.random() * 2000
    );


  }

}