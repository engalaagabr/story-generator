import { describe, expect, it } from 'vitest';
import { library, remember, storyPath } from '../lib/storage';
import { story } from './fixtures';

describe('Saved story state', () => {
  it('tolerates corrupt storage and saves references without session data', () => {
    localStorage.setItem('fable:v1:library', 'not valid JSON');
    expect(library()).toEqual([]);
    remember(story);
    remember(story);
    expect(library()).toHaveLength(1);
    expect(localStorage.getItem('fable:v1:library')).not.toContain('session');
    expect(localStorage.getItem('fable:v1:library')).not.toContain('all_nodes');
  });
  it('restores only reachable choices and never restores a loop', () => {
    localStorage.setItem('fable:v1:path:7', JSON.stringify([10, 20, 40, 10]));
    expect(storyPath(story)).toEqual([10, 20, 40]);
    localStorage.setItem('fable:v1:path:7', JSON.stringify([10, 40]));
    expect(storyPath(story)).toEqual([10]);
    localStorage.setItem('fable:v1:path:7', JSON.stringify([999]));
    expect(storyPath(story)).toEqual([10]);
  });
});
