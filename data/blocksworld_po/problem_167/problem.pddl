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
		(ontable green)
		(on purple green)
		(clear purple)

		(ontable yellow)
		(on red yellow)
		(clear red)

		(ontable orange)
		(clear orange)
		(ontable blue)
		(clear blue)
	)
	(:goal (and (handempty robot)
		(ontable purple)
		(on blue purple)
		(clear blue)
		(ontable red)
		(on orange red)
		(clear orange)

		(ontable yellow)
		(on green yellow)
		(clear green)
	))
)