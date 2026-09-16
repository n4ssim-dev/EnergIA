import { Routes } from '@angular/router';

import { Home } from './home/home';
import { Chat } from './chat/chat';
import { Accueil } from './accueil/accueil';
import { Layout } from './layout/layout';
import { Prediction } from './prediction/prediction';

export const routes: Routes = [


  {
    path: '',
    component: Accueil
  },

  // 
  {
    path: '',
    component: Layout,
    children: [
      {
        path: 'home',
        component: Home
      },
      {
        path: 'chat',
        component: Chat
      },
      {
        path: 'prediction',
        component: Prediction
      }
    ]
  },
];