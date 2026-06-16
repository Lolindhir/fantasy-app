import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { MarkdownModule } from 'ngx-markdown';
import { SharedMaterialImports } from '../../shared/shared-material-imports';

@Component({
  selector: 'app-about',
  imports: [
    MarkdownModule,
    SharedMaterialImports
  ],
  standalone: true,
  templateUrl: './about.html',
  styleUrl: './about.scss'
})
export class AboutComponent implements OnInit {

  markdownText = '';
  selectedTab = '';

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.selectedTab = 'Overview';
    this.http.get('docs/Overview.md', { responseType: 'text' })
      .subscribe(data => {
        this.markdownText = data;
      });
  }

  selectTab(tab: string) {
    this.selectedTab = tab;
    this.http.get(`docs/${tab}.md`, { responseType: 'text' })
      .subscribe(data => this.markdownText = data);
  }
}
