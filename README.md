# MangaStream Archiver
Python bot for downloading new releases from MangaStream. Its working but doesn't tested fully

- data is in sqllite database
- get manga list from site
- get chapters from manga list
- download not downnloaded chapters

## Database model

##### Manga

- name
- url
- chapters <- Chapter


##### Chapter

- name
- url
- cdn_id 
- manga -> Manga
- downloaded

 



