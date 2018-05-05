#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <retro.h>

#define LOG(...) rt_log(data, "RSound", __VA_ARGS__)


int rt_audio_init(LibraryData* data, int frequency) {
	int err;
	snd_pcm_hw_params_t* hw_params;

	if (frequency == data->private->audio.frequency)
		return 0;
	
	if (data->private->audio.frequency == 0) {
		err = snd_pcm_open(&data->private->audio.device, "default", SND_PCM_STREAM_PLAYBACK, 0);
		if (err < 0) {
			LOG(RETRO_LOG_ERROR, "Failed to open audio device: %s", snd_strerror(err));
			rt_set_error(data, "Failed to open audio device");
			return 1;
		}
		
		err = snd_pcm_hw_params_malloc(&hw_params);
		if (err < 0) {
			LOG(RETRO_LOG_ERROR, "Failed to configure audio device: Out of memory");
			rt_set_error(data, "Failed to configure audio device");
			return 1;
		}
		
		err = snd_pcm_hw_params_any(data->private->audio.device, hw_params);
		if (err < 0) {
			LOG(RETRO_LOG_ERROR, "Failed to configure audio device: snd_pcm_hw_params_any failed");
			rt_set_error(data, "Failed to configure audio device");
			return 1;
		}
		
		snd_pcm_hw_params_set_rate_resample(data->private->audio.device, hw_params, 1);
		snd_pcm_hw_params_set_access(data->private->audio.device, hw_params, SND_PCM_ACCESS_RW_INTERLEAVED);
		snd_pcm_hw_params_set_format(data->private->audio.device, hw_params, SND_PCM_FORMAT_S16_LE);
		
		err = snd_pcm_hw_params_set_channels(data->private->audio.device, hw_params, 2);
		if (err < 0) {
			LOG(RETRO_LOG_ERROR, "Failed to configure audio device: failed to set audio channels");
			rt_set_error(data, "Failed to configure audio device");
			return 1;
		}
		
		uint rate = 44100;
		err = snd_pcm_hw_params_set_rate_near(data->private->audio.device, hw_params, &rate, 0);
		if (err < 0) {
			LOG(RETRO_LOG_ERROR, "Failed to configure audio device: failed to set sample rate");
			rt_set_error(data, "Failed to configure audio device");
			return 1;
		}
		
		err = snd_pcm_hw_params(data->private->audio.device, hw_params);
		if (err < 0) {
			LOG(RETRO_LOG_ERROR, "Failed to configure audio device: snd_pcm_hw_params failed");
			rt_set_error(data, "Failed to configure audio device");
			return 1;
		}
		
		snd_pcm_hw_params_get_buffer_size(hw_params, &data->private->audio.buffer_size );
		
		err = snd_pcm_prepare(data->private->audio.device);
		if (err < 0) {
			LOG(RETRO_LOG_ERROR, "Failed to configure audio device: snd_pcm_prepare failed");
			rt_set_error(data, "Failed to configure audio device");
			return 1;
		}
	}
	
	err = snd_pcm_set_params(data->private->audio.device, SND_PCM_FORMAT_S16,
				SND_PCM_ACCESS_RW_INTERLEAVED, 2, frequency, 1, 64 * 1000);
	if (err < 0) {
		data->private->audio.frequency = 1;	// Random number just so device is not opened again in next call
		LOG(RETRO_LOG_ERROR, "Failed to configure audio device: %s", snd_strerror(err));
		rt_set_error(data, "Failed to configure audio device");
		return 1;
	}
	data->private->audio.frequency = frequency;
	
	return 0;
}


size_t rt_audio_sample_batch(LibraryData* data, const int16_t* audiodata, size_t frames) {
	snd_pcm_sframes_t r = snd_pcm_writei(data->private->audio.device, audiodata, frames);
	if (r < 0) {
		if (r == -EPIPE)
			LOG(RETRO_LOG_WARN, "Audio underrun");
		else
			LOG(RETRO_LOG_WARN, "Alsa error #%i: ", -r);
		snd_pcm_recover(data->private->audio.device, r, 0);
		return 0;
	}
	
	return r;
}


void rt_audio_sample(LibraryData* data, int16_t left, int16_t right) {
	int16_t buf[2] = {left, right};
	rt_audio_sample_batch(data, buf, 1);
}
