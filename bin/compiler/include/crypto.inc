#if defined _crypto_included
  #endinput
#endif
#define _crypto_included



/* Guided by *********************************************************************************************************************
BASE64: http://www.opensource.apple.com/source/QuickTimeStreamingServer/QuickTimeStreamingServer-452/CommonUtilitiesLib/base64.c
SHA1/SHA2: https://github.com/emn178/js-sha1 / https://github.com/emn178/js-sha512
CRC32: https://forums.alliedmods.net/showthread.php?t=206640

INC by Destro (https://amxmodx-es.com)
*********************************************************************************************************************************/


enum Sha2Bits: {
	SHA2_224,
	SHA2_256,
	SHA2_384,
	SHA2_512
}

stock SHA1_Data(const data[], size, output[], len)
{
	return __hash_sha1(data, size, output, len)
}

stock SHA1_File(const file[], output[], len)
{
	return __hash_sha1(file, -1, output, len)
}

stock SHA2_Data(const data[], size, output[], len, Sha2Bits:bits=SHA2_512)
{
	return __hash_sha2(data, size, bits, output, len)
}

stock SHA2_File(const file[], output[], len, Sha2Bits:bits=SHA2_512)
{
	return __hash_sha2(file, -1, bits, output, len)
}

stock MD5_Data(const data[], output[], len)
{
	new buff[34]
	md5(data, buff)
	
	return copy(output, len, buff)
}

stock MD5_File(const file[], output[], len)
{
	new buff[34]
	md5_file(file, buff)
	
	return copy(output, len, buff)
}

/*
stock BASE64_Encode(const data[], size=0, output[], len)
stock BASE64_Decode(const data[], output[], len)

stock CRC32_Data(const data[], size)
stock CRC32_File(const file[])

stock encrypt_key(string[])
stock encrypt(string[], out[], len, numkey)
stock decrypt(encrypted[], out[], len, numkey)
*/

/*****************************************************************************************************************/

#define READ_FILE_BUFFER	2048

stock const gCRC32_Table[] = {
	0x00000000, 0x77073096, 0xee0e612c, 0x990951ba, 0x076dc419, 0x706af48f,
	0xe963a535, 0x9e6495a3,	0x0edb8832, 0x79dcb8a4, 0xe0d5e91e, 0x97d2d988,
	0x09b64c2b, 0x7eb17cbd, 0xe7b82d07, 0x90bf1d91, 0x1db71064, 0x6ab020f2,
	0xf3b97148, 0x84be41de,	0x1adad47d, 0x6ddde4eb, 0xf4d4b551, 0x83d385c7,
	0x136c9856, 0x646ba8c0, 0xfd62f97a, 0x8a65c9ec,	0x14015c4f, 0x63066cd9,
	0xfa0f3d63, 0x8d080df5,	0x3b6e20c8, 0x4c69105e, 0xd56041e4, 0xa2677172,
	0x3c03e4d1, 0x4b04d447, 0xd20d85fd, 0xa50ab56b,	0x35b5a8fa, 0x42b2986c,
	0xdbbbc9d6, 0xacbcf940,	0x32d86ce3, 0x45df5c75, 0xdcd60dcf, 0xabd13d59,
	0x26d930ac, 0x51de003a, 0xc8d75180, 0xbfd06116, 0x21b4f4b5, 0x56b3c423,
	0xcfba9599, 0xb8bda50f, 0x2802b89e, 0x5f058808, 0xc60cd9b2, 0xb10be924,
	0x2f6f7c87, 0x58684c11, 0xc1611dab, 0xb6662d3d,	0x76dc4190, 0x01db7106,
	0x98d220bc, 0xefd5102a, 0x71b18589, 0x06b6b51f, 0x9fbfe4a5, 0xe8b8d433,
	0x7807c9a2, 0x0f00f934, 0x9609a88e, 0xe10e9818, 0x7f6a0dbb, 0x086d3d2d,
	0x91646c97, 0xe6635c01, 0x6b6b51f4, 0x1c6c6162, 0x856530d8, 0xf262004e,
	0x6c0695ed, 0x1b01a57b, 0x8208f4c1, 0xf50fc457, 0x65b0d9c6, 0x12b7e950,
	0x8bbeb8ea, 0xfcb9887c, 0x62dd1ddf, 0x15da2d49, 0x8cd37cf3, 0xfbd44c65,
	0x4db26158, 0x3ab551ce, 0xa3bc0074, 0xd4bb30e2, 0x4adfa541, 0x3dd895d7,
	0xa4d1c46d, 0xd3d6f4fb, 0x4369e96a, 0x346ed9fc, 0xad678846, 0xda60b8d0,
	0x44042d73, 0x33031de5, 0xaa0a4c5f, 0xdd0d7cc9, 0x5005713c, 0x270241aa,
	0xbe0b1010, 0xc90c2086, 0x5768b525, 0x206f85b3, 0xb966d409, 0xce61e49f,
	0x5edef90e, 0x29d9c998, 0xb0d09822, 0xc7d7a8b4, 0x59b33d17, 0x2eb40d81,
	0xb7bd5c3b, 0xc0ba6cad, 0xedb88320, 0x9abfb3b6, 0x03b6e20c, 0x74b1d29a,
	0xead54739, 0x9dd277af, 0x04db2615, 0x73dc1683, 0xe3630b12, 0x94643b84,
	0x0d6d6a3e, 0x7a6a5aa8, 0xe40ecf0b, 0x9309ff9d, 0x0a00ae27, 0x7d079eb1,
	0xf00f9344, 0x8708a3d2, 0x1e01f268, 0x6906c2fe, 0xf762575d, 0x806567cb,
	0x196c3671, 0x6e6b06e7, 0xfed41b76, 0x89d32be0, 0x10da7a5a, 0x67dd4acc,
	0xf9b9df6f, 0x8ebeeff9, 0x17b7be43, 0x60b08ed5, 0xd6d6a3e8, 0xa1d1937e,
	0x38d8c2c4, 0x4fdff252, 0xd1bb67f1, 0xa6bc5767, 0x3fb506dd, 0x48b2364b,
	0xd80d2bda, 0xaf0a1b4c, 0x36034af6, 0x41047a60, 0xdf60efc3, 0xa867df55,
	0x316e8eef, 0x4669be79, 0xcb61b38c, 0xbc66831a, 0x256fd2a0, 0x5268e236,
	0xcc0c7795, 0xbb0b4703, 0x220216b9, 0x5505262f, 0xc5ba3bbe, 0xb2bd0b28,
	0x2bb45a92, 0x5cb36a04, 0xc2d7ffa7, 0xb5d0cf31, 0x2cd99e8b, 0x5bdeae1d,
	0x9b64c2b0, 0xec63f226, 0x756aa39c, 0x026d930a, 0x9c0906a9, 0xeb0e363f,
	0x72076785, 0x05005713, 0x95bf4a82, 0xe2b87a14, 0x7bb12bae, 0x0cb61b38,
	0x92d28e9b, 0xe5d5be0d, 0x7cdcefb7, 0x0bdbdf21, 0x86d3d2d4, 0xf1d4e242,
	0x68ddb3f8, 0x1fda836e, 0x81be16cd, 0xf6b9265b, 0x6fb077e1, 0x18b74777,
	0x88085ae6, 0xff0f6a70, 0x66063bca, 0x11010b5c, 0x8f659eff, 0xf862ae69,
	0x616bffd3, 0x166ccf45, 0xa00ae278, 0xd70dd2ee, 0x4e048354, 0x3903b3c2,
	0xa7672661, 0xd06016f7, 0x4969474d, 0x3e6e77db, 0xaed16a4a, 0xd9d65adc,
	0x40df0b66, 0x37d83bf0, 0xa9bcae53, 0xdebb9ec5, 0x47b2cf7f, 0x30b5ffe9,
	0xbdbdf21c, 0xcabac28a, 0x53b39330, 0x24b4a3a6, 0xbad03605, 0xcdd70693,
	0x54de5729, 0x23d967bf, 0xb3667a2e, 0xc4614ab8, 0x5d681b02, 0x2a6f2b94,
	0xb40bbe37, 0xc30c8ea1, 0x5a05df1b, 0x2d02ef8d
}

stock const gSHA2_Table[] = {
	0x428A2F98, 0xD728AE22, 0x71374491, 0x23EF65CD,
	0xB5C0FBCF, 0xEC4D3B2F, 0xE9B5DBA5, 0x8189DBBC,
	0x3956C25B, 0xF348B538, 0x59F111F1, 0xB605D019,
	0x923F82A4, 0xAF194F9B, 0xAB1C5ED5, 0xDA6D8118,
	0xD807AA98, 0xA3030242, 0x12835B01, 0x45706FBE,
	0x243185BE, 0x4EE4B28C, 0x550C7DC3, 0xD5FFB4E2,
	0x72BE5D74, 0xF27B896F, 0x80DEB1FE, 0x3B1696B1,
	0x9BDC06A7, 0x25C71235, 0xC19BF174, 0xCF692694,
	0xE49B69C1, 0x9EF14AD2, 0xEFBE4786, 0x384F25E3,
	0x0FC19DC6, 0x8B8CD5B5, 0x240CA1CC, 0x77AC9C65,
	0x2DE92C6F, 0x592B0275, 0x4A7484AA, 0x6EA6E483,
	0x5CB0A9DC, 0xBD41FBD4, 0x76F988DA, 0x831153B5,
	0x983E5152, 0xEE66DFAB, 0xA831C66D, 0x2DB43210,
	0xB00327C8, 0x98FB213F, 0xBF597FC7, 0xBEEF0EE4,
	0xC6E00BF3, 0x3DA88FC2, 0xD5A79147, 0x930AA725,
	0x06CA6351, 0xE003826F, 0x14292967, 0x0A0E6E70,
	0x27B70A85, 0x46D22FFC, 0x2E1B2138, 0x5C26C926,
	0x4D2C6DFC, 0x5AC42AED, 0x53380D13, 0x9D95B3DF,
	0x650A7354, 0x8BAF63DE, 0x766A0ABB, 0x3C77B2A8,
	0x81C2C92E, 0x47EDAEE6, 0x92722C85, 0x1482353B,
	0xA2BFE8A1, 0x4CF10364, 0xA81A664B, 0xBC423001,
	0xC24B8B70, 0xD0F89791, 0xC76C51A3, 0x0654BE30,
	0xD192E819, 0xD6EF5218, 0xD6990624, 0x5565A910,
	0xF40E3585, 0x5771202A, 0x106AA070, 0x32BBD1B8,
	0x19A4C116, 0xB8D2D0C8, 0x1E376C08, 0x5141AB53,
	0x2748774C, 0xDF8EEB99, 0x34B0BCB5, 0xE19B48A8,
	0x391C0CB3, 0xC5C95A63, 0x4ED8AA4A, 0xE3418ACB,
	0x5B9CCA4F, 0x7763E373, 0x682E6FF3, 0xD6B2B8A3,
	0x748F82EE, 0x5DEFB2FC, 0x78A5636F, 0x43172F60,
	0x84C87814, 0xA1F0AB72, 0x8CC70208, 0x1A6439EC,
	0x90BEFFFA, 0x23631E28, 0xA4506CEB, 0xDE82BDE9,
	0xBEF9A3F7, 0xB2C67915, 0xC67178F2, 0xE372532B,
	0xCA273ECE, 0xEA26619C, 0xD186B8C7, 0x21C0C207,
	0xEADA7DD6, 0xCDE0EB1E, 0xF57D4F7F, 0xEE6ED178,
	0x06F067AA, 0x72176FBA, 0x0A637DC5, 0xA2C898A6,
	0x113F9804, 0xBEF90DAE, 0x1B710B35, 0x131C471B,
	0x28DB77F5, 0x23047D84, 0x32CAAB7B, 0x40C72493,
	0x3C9EBE0A, 0x15C9BEBC, 0x431D67C4, 0x9C100D4C,
	0x4CC5D4BE, 0xCB3E42B6, 0x597F299C, 0xFC657E2A,
	0x5FCB6FAB, 0x3AD6FAEC, 0x6C44198C, 0x4A475817
}

stock const gSHA_HEXCHAR[] = "0123456789abcdef"
stock const gSHA_EXTRA[] = { -2147483648, 8388608, 32768, 128 }
stock const gSHA_SHIFT[] = { 24, 16, 8, 0 }

stock gEncryptTable[96] // dYm4urtizlp2y@h.qsbT67n5oQf8xwU91VvcPZeB3WAk0MNHJFGKLjSgCaRDOEIX
stock gEncryptTableLen

stock const gBase64_Fill = '='
stock const gBase64_Table[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
stock const gDecode_Table[256] =
{
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 62, 64, 64, 64, 63,
    52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 64, 64, 64, 64, 64, 64,
    64,  0,  1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12, 13, 14,
    15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 64, 64, 64, 64, 64,
    64, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40,
    41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64
};


stock BASE64_Encode(const data[], size=0, output[], len)
{
	new write, i
	if(!size) size = strlen(data)
 
	for(i = 0; i < (size - 2); i += 3)
	{
		if((write + 4) >= len)
		{
			output[0] = '^0';
			return 0;
		}
	
		output[write++] = gBase64_Table[(data[i] >> 2) & 0x3F];
		output[write++] = gBase64_Table[((data[i] & 0x3) << 4) | ((data[i + 1] & 0xF0) >> 4)];
		output[write++] = gBase64_Table[((data[i + 1] & 0xF) << 2) | ((data[i + 2] & 0xC0) >> 6)];
		output[write++] = gBase64_Table[data[i + 2] & 0x3F];
	}
	
	if(i < size)
	{
		if((write + 4) >= len)
		{
			output[0] = '^0';
			return 0;
		}
	
		output[write++] = gBase64_Table[(data[i] >> 2) & 0x3F];
		
		if(i == (size - 1))
		{
			output[write++] = gBase64_Table[((data[i] & 0x3) << 4)];
			output[write++] = gBase64_Fill;
		}
		else
		{
			output[write++] = gBase64_Table[((data[i] & 0x3) << 4) | ((data[i + 1] & 0xF0) >> 4)];
			output[write++] = gBase64_Table[((data[i + 1] & 0xF) << 2)];
		}
		
		output[write++] = gBase64_Fill;
	}

	output[write] = '^0';
	return write;
}


stock BASE64_Decode(const data[], output[], len)
{
	new write, read, nprbytes

	while(gDecode_Table[data[read++]] <= 63) { }
	
	nprbytes = read - 1;
	read = 0

	while(nprbytes > 4)
	{
		if((write + 3) >= len)
		{
			output[0] = '^0';
			return 0;
		}
		
		output[write++] = (gDecode_Table[data[read]] << 2 | gDecode_Table[data[read+1]] >> 4);
		output[write++] = (gDecode_Table[data[read+1]] << 4 | gDecode_Table[data[read+2]] >> 2);
		output[write++] = (gDecode_Table[data[read+2]] << 6 | gDecode_Table[data[read+3]]);
		
		read += 4;
		nprbytes -= 4;
	}

	if((write + 1 + nprbytes) >= len)
	{
		output[0] = '^0';
		return 0;
	}
		
	if(nprbytes > 1)
		output[write++] = (gDecode_Table[data[read]] << 2 | gDecode_Table[data[read+1]] >> 4);

	if(nprbytes > 2)
		output[write++] = (gDecode_Table[data[read+1]] << 4 | gDecode_Table[data[read+2]] >> 2);
	
	if(nprbytes > 3)
		output[write++] = (gDecode_Table[data[read+2]] << 6 | gDecode_Table[data[read+3]]);
		

	output[write] = '^0';
	return write;
}

stock CRC32_Data(const data[], size)
{
	new crc = 0xFFFFFFFF
	
	for (new i = 0; i < size; i++)
	{
		crc = gCRC32_Table[(crc ^ data[i]) & 0xFF] ^ ((crc >> 8) & 0x00FFFFFF)
	}
	
	return crc ^ 0xFFFFFFFF
}

stock CRC32_File(const file[])
{
	new fp = fopen(file, "rb")
	if(!fp) return 0
	
	new crc = 0xFFFFFFFF;
	new data[READ_FILE_BUFFER], readsize, i;
	
	while((readsize = fread_blocks(fp, data, READ_FILE_BUFFER, BLOCK_CHAR)) > 0)
	{
		for (i = 0; i < readsize; i++)
		{
			crc = gCRC32_Table[(crc ^ data[i]) & 0xFF] ^ ((crc >> 8) & 0x00FFFFFF)
		}
	}
	
	fclose(fp)
	
	return crc ^ 0xFFFFFFFF
}

stock __hash_sha1(const dataORfile[], size, output[], len)
{
	new h0, h1, h2, h3, h4, block, blocks[160], code, end, t, f,
	i, j, index, start, bytes,
	fp, length, totalread, data[READ_FILE_BUFFER], data_start;
	
	if(size == -1)
	{
		fp = fopen(dataORfile, "rb");
		if(!fp)
		{
			copy(output, len, "");
			return false;
		}
		
		fseek(fp, 0, SEEK_END);
		length = ftell(fp);
		if(length == 0)
		{
			fclose(fp);
			copy(output, len, "");
			return false;
		}
		fseek(fp, 0, SEEK_SET);
		
		totalread = fread_blocks(fp, data, READ_FILE_BUFFER, BLOCK_CHAR);
	}
	else {
		length = size;
	}

	h0 = 0x67452301;
	h1 = 0xEFCDAB89;
	h2 = 0x98BADCFE;
	h3 = 0x10325476;
	h4 = 0xC3D2E1F0;

	do
	{
		blocks[0] = block;
		blocks[16] = blocks[1] = blocks[2] = blocks[3] =
		blocks[4] = blocks[5] = blocks[6] = blocks[7] =
		blocks[8] = blocks[9] = blocks[10] = blocks[11] =
		blocks[12] = blocks[13] = blocks[14] = blocks[15] = 0;
	
		for (i = start;index < length && i < 64; ++index)
		{
			if(size == -1)
			{
				if(index >= totalread)
				{
					data_start = totalread;
					totalread += fread_blocks(fp, data, READ_FILE_BUFFER, BLOCK_CHAR)

				}
	
				code = data[index-data_start];
			}
			else code = dataORfile[index];
				

			if(code < 0) code = 256 + code
				
			blocks[i >> 2] |= code << gSHA_SHIFT[i++ & 3];
		}
				
		
		bytes += i - start;
		start = i - 64;
		
		if(index == length)
		{
			blocks[i >> 2] |= gSHA_EXTRA[i & 3];
			++index;
		}
		
		block = blocks[16];
		if(index > length && i < 56)
		{
			blocks[15] = bytes << 3;
			end = true;
		}

		for(j = 16;j < 80;++j)
		{
			t = blocks[j - 3] ^ blocks[j - 8] ^ blocks[j - 14] ^ blocks[j - 16];
			blocks[j] =  (t << 1) | (t >>> 31);
		}

		new a = h0, b = h1, c = h2, d = h3, e = h4;
		for(j = 0;j < 20;j += 5)
		{
			f = (b & c) | ((~b) & d);
			t = (a << 5) | (a >>> 27);
			e = t + f + e + 1518500249 + blocks[j] << 0;
			b = (b << 30) | (b >>> 2);

			f = (a & b) | ((~a) & c);
			t = (e << 5) | (e >>> 27);
			d = t + f + d + 1518500249 + blocks[j + 1] << 0;
			a = (a << 30) | (a >>> 2);

			f = (e & a) | ((~e) & b);
			t = (d << 5) | (d >>> 27);
			c = t + f + c + 1518500249 + blocks[j + 2] << 0;
			e = (e << 30) | (e >>> 2);

			f = (d & e) | ((~d) & a);
			t = (c << 5) | (c >>> 27);
			b = t + f + b + 1518500249 + blocks[j + 3] << 0;
			d = (d << 30) | (d >>> 2);

			f = (c & d) | ((~c) & e);
			t = (b << 5) | (b >>> 27);
			a = t + f + a + 1518500249 + blocks[j + 4] << 0;
			c = (c << 30) | (c >>> 2);
		}

		for(;j < 40;j += 5)
		{
			f = b ^ c ^ d;
			t = (a << 5) | (a >>> 27);
			e = t + f + e + 1859775393 + blocks[j] << 0;
			b = (b << 30) | (b >>> 2);

			f = a ^ b ^ c;
			t = (e << 5) | (e >>> 27);
			d = t + f + d + 1859775393 + blocks[j + 1] << 0;
			a = (a << 30) | (a >>> 2);

			f = e ^ a ^ b;
			t = (d << 5) | (d >>> 27);
			c = t + f + c + 1859775393 + blocks[j + 2] << 0;
			e = (e << 30) | (e >>> 2);

			f = d ^ e ^ a;
			t = (c << 5) | (c >>> 27);
			b = t + f + b + 1859775393 + blocks[j + 3] << 0;
			d = (d << 30) | (d >>> 2);

			f = c ^ d ^ e;
			t = (b << 5) | (b >>> 27);
			a = t + f + a + 1859775393 + blocks[j + 4] << 0;
			c = (c << 30) | (c >>> 2);
		}

		for(;j < 60;j += 5)
		{
			f = (b & c) | (b & d) | (c & d);
			t = (a << 5) | (a >>> 27);
			e = t + f + e - 1894007588 + blocks[j] << 0;
			b = (b << 30) | (b >>> 2);

			f = (a & b) | (a & c) | (b & c);
			t = (e << 5) | (e >>> 27);
			d = t + f + d - 1894007588 + blocks[j + 1] << 0;
			a = (a << 30) | (a >>> 2);

			f = (e & a) | (e & b) | (a & b);
			t = (d << 5) | (d >>> 27);
			c = t + f + c - 1894007588 + blocks[j + 2] << 0;
			e = (e << 30) | (e >>> 2);

			f = (d & e) | (d & a) | (e & a);
			t = (c << 5) | (c >>> 27);
			b = t + f + b - 1894007588 + blocks[j + 3] << 0;
			d = (d << 30) | (d >>> 2);

			f = (c & d) | (c & e) | (d & e);
			t = (b << 5) | (b >>> 27);
			a = t + f + a - 1894007588 + blocks[j + 4] << 0;
			c = (c << 30) | (c >>> 2);
		}

		for(;j < 80;j += 5)
		{
			f = b ^ c ^ d;
			t = (a << 5) | (a >>> 27);
			e = t + f + e - 899497514 + blocks[j] << 0;
			b = (b << 30) | (b >>> 2);

			f = a ^ b ^ c;
			t = (e << 5) | (e >>> 27);
			d = t + f + d - 899497514 + blocks[j + 1] << 0;
			a = (a << 30) | (a >>> 2);

			f = e ^ a ^ b;
			t = (d << 5) | (d >>> 27);
			c = t + f + c - 899497514 + blocks[j + 2] << 0;
			e = (e << 30) | (e >>> 2);

			f = d ^ e ^ a;
			t = (c << 5) | (c >>> 27);
			b = t + f + b - 899497514 + blocks[j + 3] << 0;
			d = (d << 30) | (d >>> 2);

			f = c ^ d ^ e;
			t = (b << 5) | (b >>> 27);
			a = t + f + a - 899497514 + blocks[j + 4] << 0;
			c = (c << 30) | (c >>> 2);
		}

		h0 = h0 + a << 0;
		h1 = h1 + b << 0;
		h2 = h2 + c << 0;
		h3 = h3 + d << 0;
		h4 = h4 + e << 0;
	} while(!end);
	
	if(fp) fclose(fp)

	new hex[41], pos
	hex[pos++] = gSHA_HEXCHAR[(h0 >> 28) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h0 >> 24) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h0 >> 20) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h0 >> 16) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h0 >> 12) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h0 >> 8) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h0 >> 4) & 0x0F];hex[pos++] = gSHA_HEXCHAR[h0 & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h1 >> 28) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h1 >> 24) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h1 >> 20) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h1 >> 16) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h1 >> 12) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h1 >> 8) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h1 >> 4) & 0x0F];hex[pos++] = gSHA_HEXCHAR[h1 & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h2 >> 28) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h2 >> 24) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h2 >> 20) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h2 >> 16) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h2 >> 12) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h2 >> 8) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h2 >> 4) & 0x0F];hex[pos++] = gSHA_HEXCHAR[h2 & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h3 >> 28) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h3 >> 24) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h3 >> 20) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h3 >> 16) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h3 >> 12) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h3 >> 8) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h3 >> 4) & 0x0F];hex[pos++] = gSHA_HEXCHAR[h3 & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h4 >> 28) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h4 >> 24) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h4 >> 20) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h4 >> 16) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h4 >> 12) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h4 >> 8) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h4 >> 4) & 0x0F];hex[pos++] = gSHA_HEXCHAR[h4 & 0x0F]

	copy(output, len, hex)
	return true;
}

stock __hash_sha2(const dataORfile[], size, Sha2Bits:bits, output[], len)
{
	new h0h, h0l, h1h, h1l, h2h, h2l, h3h, h3l, 
	h4h, h4l, h5h, h5l, h6h, h6l, h7h, h7l, block, blocks[160], code, end,
	i, j, index, start, bytes,
	s0h, s0l, s1h, s1l, c1, c2, c3, c4, 
	abh, abl, dah, dal, cdh, cdl, bch, bcl,
	majh, majl, t1h, t1l, t2h, t2l, chh, chl,
	fp, length, totalread, data[READ_FILE_BUFFER], data_start;
	
	if(size == -1)
	{
		fp = fopen(dataORfile, "rb")
		if(!fp)
		{
			copy(output, len, "")
			return false
		}
		
		fseek(fp, 0, SEEK_END)
		length = ftell(fp)
		if(length == 0)
		{
			fclose(fp)
			copy(output, len, "")
			return false
		}
		fseek(fp, 0, SEEK_SET)
		
		totalread = fread_blocks(fp, data, READ_FILE_BUFFER, BLOCK_CHAR)
	}
	else {
		length = strlen(dataORfile)
	}
	

	if(bits == SHA2_384)
	{
		h0h = 0xCBBB9D5D;
		h0l = 0xC1059ED8;
		h1h = 0x629A292A;
		h1l = 0x367CD507;
		h2h = 0x9159015A;
		h2l = 0x3070DD17;
		h3h = 0x152FECD8;
		h3l = 0xF70E5939;
		h4h = 0x67332667;
		h4l = 0xFFC00B31;
		h5h = 0x8EB44A87;
		h5l = 0x68581511;
		h6h = 0xDB0C2E0D;
		h6l = 0x64F98FA7;
		h7h = 0x47B5481D;
		h7l = 0xBEFA4FA4;
	}
	else if(bits == SHA2_256)
	{
		h0h = 0x22312194;
		h0l = 0xFC2BF72C;
		h1h = 0x9F555FA3;
		h1l = 0xC84C64C2;
		h2h = 0x2393B86B;
		h2l = 0x6F53B151;
		h3h = 0x96387719;
		h3l = 0x5940EABD;
		h4h = 0x96283EE2;
		h4l = 0xA88EFFE3;
		h5h = 0xBE5E1E25;
		h5l = 0x53863992;
		h6h = 0x2B0199FC;
		h6l = 0x2C85B8AA;
		h7h = 0x0EB72DDC;
		h7l = 0x81C52CA2;
	}
	else if(bits == SHA2_224)
	{
		h0h = 0x8C3D37C8;
		h0l = 0x19544DA2;
		h1h = 0x73E19966;
		h1l = 0x89DCD4D6;
		h2h = 0x1DFAB7AE;
		h2l = 0x32FF9C82;
		h3h = 0x679DD514;
		h3l = 0x582F9FCF;
		h4h = 0x0F6D2B69;
		h4l = 0x7BD44DA8;
		h5h = 0x77E36F73;
		h5l = 0x04C48942;
		h6h = 0x3F9D85A8;
		h6l = 0x6A1D36C8;
		h7h = 0x1112E6AD;
		h7l = 0x91D692A1;
	}
	else { // 512
		h0h = 0x6A09E667;
		h0l = 0xF3BCC908;
		h1h = 0xBB67AE85;
		h1l = 0x84CAA73B;
		h2h = 0x3C6EF372;
		h2l = 0xFE94F82B;
		h3h = 0xA54FF53A;
		h3l = 0x5F1D36F1;
		h4h = 0x510E527F;
		h4l = 0xADE682D1;
		h5h = 0x9B05688C;
		h5l = 0x2B3E6C1F;
		h6h = 0x1F83D9AB;
		h6l = 0xFB41BD6B;
		h7h = 0x5BE0CD19;
		h7l = 0x137E2179;
		bits = SHA2_512;
	}
	
	block = 0;
	
	do {
		blocks[0] = block;
		blocks[1] = blocks[2] = blocks[3] = blocks[4] = 
		blocks[5] = blocks[6] = blocks[7] = blocks[8] = 
		blocks[9] = blocks[10] = blocks[11] = blocks[12] = 
		blocks[13] = blocks[14] = blocks[15] = blocks[16] = 
		blocks[17] = blocks[18] = blocks[19] = blocks[20] =
		blocks[21] = blocks[22] = blocks[23] = blocks[24] =
		blocks[25] = blocks[26] = blocks[27] = blocks[28] =
		blocks[29] = blocks[30] = blocks[31] = blocks[32] = 0;
		
		for (i = start;index < length && i < 128; ++index)
		{
			if(size == -1)
			{
				if(index >= totalread)
				{
					data_start = totalread;
					totalread += fread_blocks(fp, data, READ_FILE_BUFFER, BLOCK_CHAR)
				}
	
				code = data[index-data_start];
			}
			else code = dataORfile[index];
			
			if(code < 0) code = 256 + code
			
			blocks[i >> 2] |= code << gSHA_SHIFT[i++ & 3];
		}
		
		bytes += i - start;
		start = i - 128;
		
		if(index == length)
		{
			blocks[i >> 2] |= gSHA_EXTRA[i & 3];
			++index;
		}
		
		block = blocks[32];
		if(index > length && i < 112)
		{
			blocks[31] = bytes << 3;
			end = true;
		}

		for(j = 32;j < 160;j += 2)
		{
			t1h = blocks[j - 30];
			t1l = blocks[j - 29];
			s0h = ((t1h >>> 1) | (t1l << 31)) ^ ((t1h >>> 8) | (t1l << 24)) ^ (t1h >>> 7);
			s0l = ((t1l >>> 1) | (t1h << 31)) ^ ((t1l >>> 8) | (t1h << 24)) ^ ((t1l >>> 7) | t1h << 25);

			t1h = blocks[j - 4];
			t1l = blocks[j - 3];
			s1h = ((t1h >>> 19) | (t1l << 13)) ^ ((t1l >>> 29) | (t1h << 3)) ^ (t1h >>> 6);
			s1l = ((t1l >>> 19) | (t1h << 13)) ^ ((t1h >>> 29) | (t1l << 3)) ^ ((t1l >>> 6) | t1h << 26);

			t1h = blocks[j - 32];
			t1l = blocks[j - 31];
			t2h = blocks[j - 14];
			t2l = blocks[j - 13];

			c1 = (t2l & 0xFFFF) + (t1l & 0xFFFF) + (s0l & 0xFFFF) + (s1l & 0xFFFF);
			c2 = (t2l >>> 16) + (t1l >>> 16) + (s0l >>> 16) + (s1l >>> 16) + (c1 >>> 16);
			c3 = (t2h & 0xFFFF) + (t1h & 0xFFFF) + (s0h & 0xFFFF) + (s1h & 0xFFFF) + (c2 >>> 16);
			c4 = (t2h >>> 16) + (t1h >>> 16) + (s0h >>> 16) + (s1h >>> 16) + (c3 >>> 16);

			blocks[j] = (c4 << 16) | (c3 & 0xFFFF);
			blocks[j + 1] = (c2 << 16) | (c1 & 0xFFFF);
		}

		new ah = h0h, al = h0l, bh = h1h, bl = h1l, ch = h2h, cl = h2l, dh = h3h, dl = h3l, eh = h4h, el = h4l, fh = h5h, fl = h5l, gh = h6h, gl = h6l, hh = h7h, hl = h7l;
		bch = bh & ch;
		bcl = bl & cl;
		
		for(j = 0;j < 160;j += 8)
		{
			s0h = ((ah >>> 28) | (al << 4)) ^ ((al >>> 2) | (ah << 30)) ^ ((al >>> 7) | (ah << 25));
			s0l = ((al >>> 28) | (ah << 4)) ^ ((ah >>> 2) | (al << 30)) ^ ((ah >>> 7) | (al << 25));

			s1h = ((eh >>> 14) | (el << 18)) ^ ((eh >>> 18) | (el << 14)) ^ ((el >>> 9) | (eh << 23));
			s1l = ((el >>> 14) | (eh << 18)) ^ ((el >>> 18) | (eh << 14)) ^ ((eh >>> 9) | (el << 23));

			abh = ah & bh;
			abl = al & bl;
			majh = abh ^ (ah & ch) ^ bch;
			majl = abl ^ (al & cl) ^ bcl;

			chh = (eh & fh) ^ (~eh & gh);
			chl = (el & fl) ^ (~el & gl);

			t1h = blocks[j];
			t1l = blocks[j + 1];
			t2h = gSHA2_Table[j];
			t2l = gSHA2_Table[j + 1];

			c1 = (t2l & 0xFFFF) + (t1l & 0xFFFF) + (chl & 0xFFFF) + (s1l & 0xFFFF) + (hl & 0xFFFF);
			c2 = (t2l >>> 16) + (t1l >>> 16) + (chl >>> 16) + (s1l >>> 16) + (hl >>> 16) + (c1 >>> 16);
			c3 = (t2h & 0xFFFF) + (t1h & 0xFFFF) + (chh & 0xFFFF) + (s1h & 0xFFFF) + (hh & 0xFFFF) + (c2 >>> 16);
			c4 = (t2h >>> 16) + (t1h >>> 16) + (chh >>> 16) + (s1h >>> 16) + (hh >>> 16) + (c3 >>> 16);

			t1h = (c4 << 16) | (c3 & 0xFFFF);
			t1l = (c2 << 16) | (c1 & 0xFFFF);

			c1 = (majl & 0xFFFF) + (s0l & 0xFFFF);
			c2 = (majl >>> 16) + (s0l >>> 16) + (c1 >>> 16);
			c3 = (majh & 0xFFFF) + (s0h & 0xFFFF) + (c2 >>> 16);
			c4 = (majh >>> 16) + (s0h >>> 16) + (c3 >>> 16);

			t2h = (c4 << 16) | (c3 & 0xFFFF);
			t2l = (c2 << 16) | (c1 & 0xFFFF);

			c1 = (dl & 0xFFFF) + (t1l & 0xFFFF);
			c2 = (dl >>> 16) + (t1l >>> 16) + (c1 >>> 16);
			c3 = (dh & 0xFFFF) + (t1h & 0xFFFF) + (c2 >>> 16);
			c4 = (dh >>> 16) + (t1h >>> 16) + (c3 >>> 16);

			hh = (c4 << 16) | (c3 & 0xFFFF);
			hl = (c2 << 16) | (c1 & 0xFFFF);

			c1 = (t2l & 0xFFFF) + (t1l & 0xFFFF);
			c2 = (t2l >>> 16) + (t1l >>> 16) + (c1 >>> 16);
			c3 = (t2h & 0xFFFF) + (t1h & 0xFFFF) + (c2 >>> 16);
			c4 = (t2h >>> 16) + (t1h >>> 16) + (c3 >>> 16);

			dh = (c4 << 16) | (c3 & 0xFFFF);
			dl = (c2 << 16) | (c1 & 0xFFFF);

			s0h = ((dh >>> 28) | (dl << 4)) ^ ((dl >>> 2) | (dh << 30)) ^ ((dl >>> 7) | (dh << 25));
			s0l = ((dl >>> 28) | (dh << 4)) ^ ((dh >>> 2) | (dl << 30)) ^ ((dh >>> 7) | (dl << 25));

			s1h = ((hh >>> 14) | (hl << 18)) ^ ((hh >>> 18) | (hl << 14)) ^ ((hl >>> 9) | (hh << 23));
			s1l = ((hl >>> 14) | (hh << 18)) ^ ((hl >>> 18) | (hh << 14)) ^ ((hh >>> 9) | (hl << 23));

			dah = dh & ah;
			dal = dl & al;
			majh = dah ^ (dh & bh) ^ abh;
			majl = dal ^ (dl & bl) ^ abl;

			chh = (hh & eh) ^ (~hh & fh);
			chl = (hl & el) ^ (~hl & fl);

			t1h = blocks[j + 2];
			t1l = blocks[j + 3];
			t2h = gSHA2_Table[j + 2];
			t2l = gSHA2_Table[j + 3];

			c1 = (t2l & 0xFFFF) + (t1l & 0xFFFF) + (chl & 0xFFFF) + (s1l & 0xFFFF) + (gl & 0xFFFF);
			c2 = (t2l >>> 16) + (t1l >>> 16) + (chl >>> 16) + (s1l >>> 16) + (gl >>> 16) + (c1 >>> 16);
			c3 = (t2h & 0xFFFF) + (t1h & 0xFFFF) + (chh & 0xFFFF) + (s1h & 0xFFFF) + (gh & 0xFFFF) + (c2 >>> 16);
			c4 = (t2h >>> 16) + (t1h >>> 16) + (chh >>> 16) + (s1h >>> 16) + (gh >>> 16) + (c3 >>> 16);

			t1h = (c4 << 16) | (c3 & 0xFFFF);
			t1l = (c2 << 16) | (c1 & 0xFFFF);

			c1 = (majl & 0xFFFF) + (s0l & 0xFFFF);
			c2 = (majl >>> 16) + (s0l >>> 16) + (c1 >>> 16);
			c3 = (majh & 0xFFFF) + (s0h & 0xFFFF) + (c2 >>> 16);
			c4 = (majh >>> 16) + (s0h >>> 16) + (c3 >>> 16);

			t2h = (c4 << 16) | (c3 & 0xFFFF);
			t2l = (c2 << 16) | (c1 & 0xFFFF);

			c1 = (cl & 0xFFFF) + (t1l & 0xFFFF);
			c2 = (cl >>> 16) + (t1l >>> 16) + (c1 >>> 16);
			c3 = (ch & 0xFFFF) + (t1h & 0xFFFF) + (c2 >>> 16);
			c4 = (ch >>> 16) + (t1h >>> 16) + (c3 >>> 16);

			gh = (c4 << 16) | (c3 & 0xFFFF);
			gl = (c2 << 16) | (c1 & 0xFFFF);

			c1 = (t2l & 0xFFFF) + (t1l & 0xFFFF);
			c2 = (t2l >>> 16) + (t1l >>> 16) + (c1 >>> 16);
			c3 = (t2h & 0xFFFF) + (t1h & 0xFFFF) + (c2 >>> 16);
			c4 = (t2h >>> 16) + (t1h >>> 16) + (c3 >>> 16);

			ch = (c4 << 16) | (c3 & 0xFFFF);
			cl = (c2 << 16) | (c1 & 0xFFFF);

			s0h = ((ch >>> 28) | (cl << 4)) ^ ((cl >>> 2) | (ch << 30)) ^ ((cl >>> 7) | (ch << 25));
			s0l = ((cl >>> 28) | (ch << 4)) ^ ((ch >>> 2) | (cl << 30)) ^ ((ch >>> 7) | (cl << 25));

			s1h = ((gh >>> 14) | (gl << 18)) ^ ((gh >>> 18) | (gl << 14)) ^ ((gl >>> 9) | (gh << 23));
			s1l = ((gl >>> 14) | (gh << 18)) ^ ((gl >>> 18) | (gh << 14)) ^ ((gh >>> 9) | (gl << 23));

			cdh = ch & dh;
			cdl = cl & dl;
			majh = cdh ^ (ch & ah) ^ dah;
			majl = cdl ^ (cl & al) ^ dal;

			chh = (gh & hh) ^ (~gh & eh);
			chl = (gl & hl) ^ (~gl & el);

			t1h = blocks[j + 4];
			t1l = blocks[j + 5];
			t2h = gSHA2_Table[j + 4];
			t2l = gSHA2_Table[j + 5];

			c1 = (t2l & 0xFFFF) + (t1l & 0xFFFF) + (chl & 0xFFFF) + (s1l & 0xFFFF) + (fl & 0xFFFF);
			c2 = (t2l >>> 16) + (t1l >>> 16) + (chl >>> 16) + (s1l >>> 16) + (fl >>> 16) + (c1 >>> 16);
			c3 = (t2h & 0xFFFF) + (t1h & 0xFFFF) + (chh & 0xFFFF) + (s1h & 0xFFFF) + (fh & 0xFFFF) + (c2 >>> 16);
			c4 = (t2h >>> 16) + (t1h >>> 16) + (chh >>> 16) + (s1h >>> 16) + (fh >>> 16) + (c3 >>> 16);

			t1h = (c4 << 16) | (c3 & 0xFFFF);
			t1l = (c2 << 16) | (c1 & 0xFFFF);

			c1 = (majl & 0xFFFF) + (s0l & 0xFFFF);
			c2 = (majl >>> 16) + (s0l >>> 16) + (c1 >>> 16);
			c3 = (majh & 0xFFFF) + (s0h & 0xFFFF) + (c2 >>> 16);
			c4 = (majh >>> 16) + (s0h >>> 16) + (c3 >>> 16);

			t2h = (c4 << 16) | (c3 & 0xFFFF);
			t2l = (c2 << 16) | (c1 & 0xFFFF);

			c1 = (bl & 0xFFFF) + (t1l & 0xFFFF);
			c2 = (bl >>> 16) + (t1l >>> 16) + (c1 >>> 16);
			c3 = (bh & 0xFFFF) + (t1h & 0xFFFF) + (c2 >>> 16);
			c4 = (bh >>> 16) + (t1h >>> 16) + (c3 >>> 16);

			fh = (c4 << 16) | (c3 & 0xFFFF);
			fl = (c2 << 16) | (c1 & 0xFFFF);

			c1 = (t2l & 0xFFFF) + (t1l & 0xFFFF);
			c2 = (t2l >>> 16) + (t1l >>> 16) + (c1 >>> 16);
			c3 = (t2h & 0xFFFF) + (t1h & 0xFFFF) + (c2 >>> 16);
			c4 = (t2h >>> 16) + (t1h >>> 16) + (c3 >>> 16);

			bh = (c4 << 16) | (c3 & 0xFFFF);
			bl = (c2 << 16) | (c1 & 0xFFFF);

			s0h = ((bh >>> 28) | (bl << 4)) ^ ((bl >>> 2) | (bh << 30)) ^ ((bl >>> 7) | (bh << 25));
			s0l = ((bl >>> 28) | (bh << 4)) ^ ((bh >>> 2) | (bl << 30)) ^ ((bh >>> 7) | (bl << 25));

			s1h = ((fh >>> 14) | (fl << 18)) ^ ((fh >>> 18) | (fl << 14)) ^ ((fl >>> 9) | (fh << 23));
			s1l = ((fl >>> 14) | (fh << 18)) ^ ((fl >>> 18) | (fh << 14)) ^ ((fh >>> 9) | (fl << 23));

			bch = bh & ch;
			bcl = bl & cl;
			majh = bch ^ (bh & dh) ^ cdh;
			majl = bcl ^ (bl & dl) ^ cdl;

			chh = (fh & gh) ^ (~fh & hh);
			chl = (fl & gl) ^ (~fl & hl);

			t1h = blocks[j + 6];
			t1l = blocks[j + 7];
			t2h = gSHA2_Table[j + 6];
			t2l = gSHA2_Table[j + 7];

			c1 = (t2l & 0xFFFF) + (t1l & 0xFFFF) + (chl & 0xFFFF) + (s1l & 0xFFFF) + (el & 0xFFFF);
			c2 = (t2l >>> 16) + (t1l >>> 16) + (chl >>> 16) + (s1l >>> 16) + (el >>> 16) + (c1 >>> 16);
			c3 = (t2h & 0xFFFF) + (t1h & 0xFFFF) + (chh & 0xFFFF) + (s1h & 0xFFFF) + (eh & 0xFFFF) + (c2 >>> 16);
			c4 = (t2h >>> 16) + (t1h >>> 16) + (chh >>> 16) + (s1h >>> 16) + (eh >>> 16) + (c3 >>> 16);

			t1h = (c4 << 16) | (c3 & 0xFFFF);
			t1l = (c2 << 16) | (c1 & 0xFFFF);

			c1 = (majl & 0xFFFF) + (s0l & 0xFFFF);
			c2 = (majl >>> 16) + (s0l >>> 16) + (c1 >>> 16);
			c3 = (majh & 0xFFFF) + (s0h & 0xFFFF) + (c2 >>> 16);
			c4 = (majh >>> 16) + (s0h >>> 16) + (c3 >>> 16);

			t2h = (c4 << 16) | (c3 & 0xFFFF);
			t2l = (c2 << 16) | (c1 & 0xFFFF);

			c1 = (al & 0xFFFF) + (t1l & 0xFFFF);
			c2 = (al >>> 16) + (t1l >>> 16) + (c1 >>> 16);
			c3 = (ah & 0xFFFF) + (t1h & 0xFFFF) + (c2 >>> 16);
			c4 = (ah >>> 16) + (t1h >>> 16) + (c3 >>> 16);

			eh = (c4 << 16) | (c3 & 0xFFFF);
			el = (c2 << 16) | (c1 & 0xFFFF);

			c1 = (t2l & 0xFFFF) + (t1l & 0xFFFF);
			c2 = (t2l >>> 16) + (t1l >>> 16) + (c1 >>> 16);
			c3 = (t2h & 0xFFFF) + (t1h & 0xFFFF) + (c2 >>> 16);
			c4 = (t2h >>> 16) + (t1h >>> 16) + (c3 >>> 16);

			ah = (c4 << 16) | (c3 & 0xFFFF);
			al = (c2 << 16) | (c1 & 0xFFFF);
		}

		c1 = (h0l & 0xFFFF) + (al & 0xFFFF);
		c2 = (h0l >>> 16) + (al >>> 16) + (c1 >>> 16);
		c3 = (h0h & 0xFFFF) + (ah & 0xFFFF) + (c2 >>> 16);
		c4 = (h0h >>> 16) + (ah >>> 16) + (c3 >>> 16);

		h0h = (c4 << 16) | (c3 & 0xFFFF);
		h0l = (c2 << 16) | (c1 & 0xFFFF);

		c1 = (h1l & 0xFFFF) + (bl & 0xFFFF);
		c2 = (h1l >>> 16) + (bl >>> 16) + (c1 >>> 16);
		c3 = (h1h & 0xFFFF) + (bh & 0xFFFF) + (c2 >>> 16);
		c4 = (h1h >>> 16) + (bh >>> 16) + (c3 >>> 16);

		h1h = (c4 << 16) | (c3 & 0xFFFF);
		h1l = (c2 << 16) | (c1 & 0xFFFF);

		c1 = (h2l & 0xFFFF) + (cl & 0xFFFF);
		c2 = (h2l >>> 16) + (cl >>> 16) + (c1 >>> 16);
		c3 = (h2h & 0xFFFF) + (ch & 0xFFFF) + (c2 >>> 16);
		c4 = (h2h >>> 16) + (ch >>> 16) + (c3 >>> 16);

		h2h = (c4 << 16) | (c3 & 0xFFFF);
		h2l = (c2 << 16) | (c1 & 0xFFFF);

		c1 = (h3l & 0xFFFF) + (dl & 0xFFFF);
		c2 = (h3l >>> 16) + (dl >>> 16) + (c1 >>> 16);
		c3 = (h3h & 0xFFFF) + (dh & 0xFFFF) + (c2 >>> 16);
		c4 = (h3h >>> 16) + (dh >>> 16) + (c3 >>> 16);

		h3h = (c4 << 16) | (c3 & 0xFFFF);
		h3l = (c2 << 16) | (c1 & 0xFFFF);

		c1 = (h4l & 0xFFFF) + (el & 0xFFFF);
		c2 = (h4l >>> 16) + (el >>> 16) + (c1 >>> 16);
		c3 = (h4h & 0xFFFF) + (eh & 0xFFFF) + (c2 >>> 16);
		c4 = (h4h >>> 16) + (eh >>> 16) + (c3 >>> 16);

		h4h = (c4 << 16) | (c3 & 0xFFFF);
		h4l = (c2 << 16) | (c1 & 0xFFFF);

		c1 = (h5l & 0xFFFF) + (fl & 0xFFFF);
		c2 = (h5l >>> 16) + (fl >>> 16) + (c1 >>> 16);
		c3 = (h5h & 0xFFFF) + (fh & 0xFFFF) + (c2 >>> 16);
		c4 = (h5h >>> 16) + (fh >>> 16) + (c3 >>> 16);

		h5h = (c4 << 16) | (c3 & 0xFFFF);
		h5l = (c2 << 16) | (c1 & 0xFFFF);

		c1 = (h6l & 0xFFFF) + (gl & 0xFFFF);
		c2 = (h6l >>> 16) + (gl >>> 16) + (c1 >>> 16);
		c3 = (h6h & 0xFFFF) + (gh & 0xFFFF) + (c2 >>> 16);
		c4 = (h6h >>> 16) + (gh >>> 16) + (c3 >>> 16);

		h6h = (c4 << 16) | (c3 & 0xFFFF);
		h6l = (c2 << 16) | (c1 & 0xFFFF);

		c1 = (h7l & 0xFFFF) + (hl & 0xFFFF);
		c2 = (h7l >>> 16) + (hl >>> 16) + (c1 >>> 16);
		c3 = (h7h & 0xFFFF) + (hh & 0xFFFF) + (c2 >>> 16);
		c4 = (h7h >>> 16) + (hh >>> 16) + (c3 >>> 16);

		h7h = (c4 << 16) | (c3 & 0xFFFF);
		h7l = (c2 << 16) | (c1 & 0xFFFF);
	} while(!end);

	if(fp) fclose(fp)
	
	new hex[129], pos
	hex[pos++] = gSHA_HEXCHAR[(h0h >> 28) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h0h >> 24) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h0h >> 20) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h0h >> 16) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h0h >> 12) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h0h >> 8) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h0h >> 4) & 0x0F];hex[pos++] = gSHA_HEXCHAR[h0h & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h0l >> 28) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h0l >> 24) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h0l >> 20) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h0l >> 16) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h0l >> 12) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h0l >> 8) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h0l >> 4) & 0x0F];hex[pos++] = gSHA_HEXCHAR[h0l & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h1h >> 28) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h1h >> 24) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h1h >> 20) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h1h >> 16) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h1h >> 12) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h1h >> 8) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h1h >> 4) & 0x0F];hex[pos++] = gSHA_HEXCHAR[h1h & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h1l >> 28) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h1l >> 24) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h1l >> 20) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h1l >> 16) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h1l >> 12) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h1l >> 8) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h1l >> 4) & 0x0F];hex[pos++] = gSHA_HEXCHAR[h1l & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h2h >> 28) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h2h >> 24) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h2h >> 20) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h2h >> 16) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h2h >> 12) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h2h >> 8) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h2h >> 4) & 0x0F];hex[pos++] = gSHA_HEXCHAR[h2h & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h2l >> 28) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h2l >> 24) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h2l >> 20) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h2l >> 16) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h2l >> 12) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h2l >> 8) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h2l >> 4) & 0x0F];hex[pos++] = gSHA_HEXCHAR[h2l & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h3h >> 28) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h3h >> 24) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h3h >> 20) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h3h >> 16) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h3h >> 12) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h3h >> 8) & 0x0F]
	hex[pos++] = gSHA_HEXCHAR[(h3h >> 4) & 0x0F];hex[pos++] = gSHA_HEXCHAR[h3h & 0x0F]
		
	if(bits >= SHA2_256)
	{
		hex[pos++] = gSHA_HEXCHAR[(h3l >> 28) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h3l >> 24) & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h3l >> 20) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h3l >> 16) & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h3l >> 12) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h3l >> 8) & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h3l >> 4) & 0x0F]; hex[pos++] = gSHA_HEXCHAR[h3l & 0x0F]
	}
		
	if(bits >= SHA2_384)
	{
		hex[pos++] = gSHA_HEXCHAR[(h4h >> 28) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h4h >> 24) & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h4h >> 20) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h4h >> 16) & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h4h >> 12) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h4h >> 8) & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h4h >> 4) & 0x0F]; hex[pos++] = gSHA_HEXCHAR[h4h & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h4l >> 28) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h4l >> 24) & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h4l >> 20) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h4l >> 16) & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h4l >> 12) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h4l >> 8) & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h4l >> 4) & 0x0F]; hex[pos++] = gSHA_HEXCHAR[h4l & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h5h >> 28) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h5h >> 24) & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h5h >> 20) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h5h >> 16) & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h5h >> 12) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h5h >> 8) & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h5h >> 4) & 0x0F]; hex[pos++] = gSHA_HEXCHAR[h5h & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h5l >> 28) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h5l >> 24) & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h5l >> 20) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h5l >> 16) & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h5l >> 12) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h5l >> 8) & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h5l >> 4) & 0x0F]; hex[pos++] = gSHA_HEXCHAR[h5l & 0x0F]
	}
		
	if(bits == SHA2_512)
	{
		hex[pos++] = gSHA_HEXCHAR[(h6h >> 28) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h6h >> 24) & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h6h >> 20) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h6h >> 16) & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h6h >> 12) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h6h >> 8) & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h6h >> 4) & 0x0F]; hex[pos++] = gSHA_HEXCHAR[h6h & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h6l >> 28) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h6l >> 24) & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h6l >> 20) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h6l >> 16) & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h6l >> 12) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h6l >> 8) & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h6l >> 4) & 0x0F]; hex[pos++] = gSHA_HEXCHAR[h6l & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h7h >> 28) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h7h >> 24) & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h7h >> 20) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h7h >> 16) & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h7h >> 12) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h7h >> 8) & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h7h >> 4) & 0x0F]; hex[pos++] = gSHA_HEXCHAR[h7h & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h7l >> 28) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h7l >> 24) & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h7l >> 20) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h7l >> 16) & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h7l >> 12) & 0x0F];hex[pos++] = gSHA_HEXCHAR[(h7l >> 8) & 0x0F]
		hex[pos++] = gSHA_HEXCHAR[(h7l >> 4) & 0x0F]; hex[pos++] = gSHA_HEXCHAR[h7l & 0x0F]
	}
	
	copy(output, len, hex)
	return true;
}

stock encrypt_init(table[])
{
	copy(gEncryptTable, charsmax(gEncryptTable), table)
	gEncryptTableLen = strlen(gEncryptTable) - 1
}

stock encrypt_key(string[])
{
	new int[1]
	for(new i; i < 4 && string[i]; i++) int{i} = string[i]
    
	return 1+int[0]%255
}

stock encrypt(string[], out[], len, numkey)
{
	if(!gEncryptTableLen) return;
	
	new charid, i
	for(i=0; string[i] && i <= len;i++)
	{
		charid = table_find_char(string[i])
		if(charid == -1) out[i] = string[i]
		else out[i] = gEncryptTable[(charid+numkey)%gEncryptTableLen]
	}
}

stock decrypt(encrypted[], out[], len, numkey)
{
	if(!gEncryptTableLen) return;
	
	new charid, i
	for(i=0; encrypted[i] && i <= len;i++)
	{
		charid = table_find_char(encrypted[i])
		if(charid == -1) out[i] = encrypted[i]
		else out[i] = gEncryptTable[(charid-numkey)%gEncryptTableLen]
	}
}

stock table_find_char(character)
{
	for(new i; gEncryptTable[i]; i++) if(gEncryptTable[i] == character) return i
    
	return -1
}
/* AMXX-Studio Notes - DO NOT MODIFY BELOW HERE
*{\\ rtf1\\ ansi\\ deff0{\\ fonttbl{\\ f0\\ fnil Tahoma;}}\n\\ viewkind4\\ uc1\\ pard\\ lang11274\\ f0\\ fs16 \n\\ par }
*/
