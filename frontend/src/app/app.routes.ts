import { Routes } from '@angular/router';

import { Home } from './home/home';
import { Chat } from './chat/chat';
import { Accueil } from './accueil/accueil';
import { Layout } from './layout/layout';

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
      }
    ]
  },
];