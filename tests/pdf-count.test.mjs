import {test} from 'node:test';
import assert from 'node:assert/strict';
import {countText} from '../src/pdf-count.mjs';
import {validate,empty} from '../src/core.mjs';
test('Korean, whitespace and punctuation',()=>assert.deepEqual(countText('안녕 세계!\nA\tB'),{withSpaces:9,withoutSpaces:7}));
test('combined Korean and emoji count as visible characters',()=>assert.deepEqual(countText('한👨‍👩‍👧‍👦é'),{withSpaces:3,withoutSpaces:3}));
test('empty scan text',()=>assert.deepEqual(countText(''),{withSpaces:0,withoutSpaces:0}));
test('PDF favorites survive backup validation',()=>assert.deepEqual(validate({...empty(),favoriteIds:['pdf-counter']}).favoriteIds,['pdf-counter']));
