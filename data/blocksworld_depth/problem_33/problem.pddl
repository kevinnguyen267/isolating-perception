(define (problem blocksworld)
	(:domain blocksworld)
	(:objects
		blue - block
		green - block
		orange - block
		purple - block
		red - block
		yellow - block
		robot - robot
	)
	(:init (handempty robot)
		(ontable blue)
		(clear blue)
		(ontable yellow)
		(on green yellow)
		(clear green)

		(ontable orange)
		(on purple orange)
		(on red purple)
		(clear red)
	)
	(:goal (and (handempty robot)
		(ontable orange)
		(clear orange)
		(ontable yellow)
		(on green yellow)
		(clear green)

		(ontable blue)
		(clear blue)
		(ontable red)
		(on purple red)
		(clear purple)
	))
)